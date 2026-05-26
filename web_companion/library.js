export const SCHEMA_VERSION = "profiprompt-library-v1";

export function normalizeLibraryPayload(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("Die Bibliothek ist kein gültiges JSON-Objekt.");
  }
  if (payload.schema_version !== SCHEMA_VERSION) {
    throw new Error(
      `Unerwartete schema_version: ${payload.schema_version ?? "leer"}. ` +
        `Erwartet wird ${SCHEMA_VERSION}.`,
    );
  }

  const prompts = ensureArray(payload.prompts).map(normalizePrompt);
  const boards = ensureArray(payload.boards).map(normalizeBoard);
  const tags = [...new Set(ensureStringArray(payload.tags))].sort((a, b) =>
    a.localeCompare(b, "de", { sensitivity: "base" }),
  );

  return {
    schema_version: SCHEMA_VERSION,
    app: normalizeApp(payload.app),
    stats: normalizeStats(payload.stats, prompts, boards),
    tags,
    prompts,
    boards,
  };
}

export function filterPrompts(library, options = {}) {
  const query = normalizeQuery(options.query);
  const boardId = options.boardId ?? "all";
  const boardsByPrompt = buildBoardsByPrompt(library);

  return library.prompts.filter((prompt) => {
    const allowedByBoard =
      boardId === "all" ||
      library.boards.some(
        (board) =>
          board.id === boardId &&
          board.items.some((item) => item.prompt_id === prompt.id),
      );
    if (!allowedByBoard) {
      return false;
    }
    if (!query) {
      return true;
    }
    return buildPromptSearchHaystack(prompt, boardsByPrompt.get(prompt.id) ?? []).includes(query);
  });
}

export function resolveBoardEntries(library, board) {
  const promptsById = new Map(library.prompts.map((prompt) => [prompt.id, prompt]));
  return board.items
    .map((item) => {
      const prompt = promptsById.get(item.prompt_id);
      if (!prompt) {
        return null;
      }
      const version =
        item.version_id == null
          ? null
          : prompt.versions.find((candidate) => candidate.id === item.version_id) ?? null;
      return { item, prompt, version };
    })
    .filter(Boolean);
}

export function resolveSelectedVersion(prompt, versionId) {
  if (!prompt || !versionId) {
    return null;
  }
  return prompt.versions.find((version) => version.id === versionId) ?? null;
}

export function summarizeLibrary(library) {
  return {
    promptCount: library.prompts.length,
    versionCount: library.prompts.reduce((sum, prompt) => sum + prompt.versions.length, 0),
    boardCount: library.boards.length,
    tagCount: library.tags.length,
  };
}

export function buildCopyText(prompt, version = null, options = {}) {
  const mode = options.mode ?? "all";
  const includeMetadata = options.includeMetadata ?? true;
  const title = version?.title ?? prompt.title;
  const text = version?.text ?? prompt.text;
  const result = version?.result ?? prompt.last_result ?? "";
  const tags = version?.tags?.length ? version.tags : prompt.tags;
  const parts = [];

  if (mode === "title") {
    parts.push(title);
  } else if (mode === "text") {
    parts.push(text);
  } else if (mode === "result") {
    parts.push(result);
  } else {
    parts.push(`${title}\n\n${text}`);
    if ((result ?? "").trim()) {
      parts.push(`--- Ergebnis ---\n${result}`);
    }
  }

  if (includeMetadata) {
    parts.push(`[Tags: ${tags.length ? tags.join(", ") : "–"}]`);
  }
  return parts.join("\n");
}

export function serializeLibrary(library) {
  return JSON.stringify(library);
}

export function parseStoredLibrary(raw) {
  if (!raw) {
    return null;
  }
  return normalizeLibraryPayload(JSON.parse(raw));
}

function normalizeApp(app) {
  return {
    name: ensureString(app?.name),
    version: ensureString(app?.version),
    exported_at: ensureString(app?.exported_at),
  };
}

function normalizeStats(stats, prompts, boards) {
  const versionCount = prompts.reduce((sum, prompt) => sum + prompt.versions.length, 0);
  const boardItemCount = boards.reduce((sum, board) => sum + board.items.length, 0);
  return {
    prompt_count: ensureNumber(stats?.prompt_count, prompts.length),
    version_count: ensureNumber(stats?.version_count, versionCount),
    board_count: ensureNumber(stats?.board_count, boards.length),
    board_item_count: ensureNumber(stats?.board_item_count, boardItemCount),
  };
}

function normalizePrompt(prompt) {
  return {
    id: ensureString(prompt?.id),
    title: ensureString(prompt?.title),
    purpose: ensureString(prompt?.purpose),
    text: ensureString(prompt?.text),
    tags: ensureStringArray(prompt?.tags),
    last_result: ensureString(prompt?.last_result),
    created_at: ensureString(prompt?.created_at),
    updated_at: ensureString(prompt?.updated_at),
    versions: ensureArray(prompt?.versions).map(normalizeVersion),
  };
}

function normalizeVersion(version) {
  return {
    id: ensureString(version?.id),
    prompt_id: ensureString(version?.prompt_id),
    version_number: ensureNumber(version?.version_number, 0),
    title: ensureString(version?.title),
    text: ensureString(version?.text),
    result: ensureString(version?.result),
    tags: ensureStringArray(version?.tags),
    created_at: ensureString(version?.created_at),
    updated_at: ensureString(version?.updated_at),
  };
}

function normalizeBoard(board) {
  return {
    id: ensureString(board?.id),
    title: ensureString(board?.title),
    description: ensureString(board?.description),
    created_at: ensureString(board?.created_at),
    items: ensureArray(board?.items).map(normalizeBoardItem),
  };
}

function normalizeBoardItem(item) {
  return {
    id: ensureString(item?.id),
    board_id: ensureString(item?.board_id),
    prompt_id: ensureString(item?.prompt_id),
    version_id: item?.version_id == null ? null : ensureString(item.version_id),
    created_at: ensureString(item?.created_at),
  };
}

function buildBoardsByPrompt(library) {
  const boardsByPrompt = new Map();
  for (const board of library.boards) {
    for (const item of board.items) {
      const list = boardsByPrompt.get(item.prompt_id) ?? [];
      list.push(board);
      boardsByPrompt.set(item.prompt_id, list);
    }
  }
  return boardsByPrompt;
}

function buildPromptSearchHaystack(prompt, boards) {
  const values = [
    prompt.title,
    prompt.purpose,
    prompt.text,
    prompt.last_result,
    ...prompt.tags,
    ...boards.flatMap((board) => [board.title, board.description]),
    ...prompt.versions.flatMap((version) => [
      version.title,
      version.text,
      version.result,
      ...version.tags,
    ]),
  ];
  return normalizeQuery(values.join("\n"));
}

function normalizeQuery(value) {
  return ensureString(value).trim().toLocaleLowerCase("de");
}

function ensureArray(value) {
  return Array.isArray(value) ? value : [];
}

function ensureStringArray(value) {
  return ensureArray(value)
    .map((entry) => ensureString(entry).trim())
    .filter(Boolean);
}

function ensureString(value) {
  return typeof value === "string" ? value : "";
}

function ensureNumber(value, fallback) {
  return Number.isFinite(value) ? value : fallback;
}
