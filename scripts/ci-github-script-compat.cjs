const assert = require("node:assert/strict");
const fs = require("node:fs");

module.exports = async function verifyGithubScript({ getOctokit }) {
  assert.equal(typeof getOctokit, "function", "v9 must inject getOctokit");
  const lines = fs.readFileSync(".github/workflows/auto-assign.yml", "utf8").split(/\r?\n/);
  const start = lines.findIndex(line => /^ {10}script: \|\s*$/.test(line));
  assert.ok(start >= 0, "auto-assign script block must exist");
  const body = [];
  for (const line of lines.slice(start + 1)) {
    if (line.trim() === "") body.push("");
    else if (line.startsWith("            ")) body.push(line.slice(12));
    else break;
  }
  assert.ok(body.some(line => line.includes("github.rest.issues.addAssignees")));
  const calls = [];
  const github = { rest: {
    repos: { get: async args => {
      calls.push(["get", args]);
      return { data: { owner: { login: "synthetic-owner" } } };
    } },
    issues: { addAssignees: async args => { calls.push(["assign", args]); } },
  } };
  const context = { repo: { owner: "synthetic-org", repo: "synthetic-repo" },
    payload: { pull_request: { number: 123 } } };
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  await new AsyncFunction("github", "context", "getOctokit", body.join("\n"))(
    github, context, getOctokit,
  );
  assert.deepEqual(calls, [
    ["get", { owner: "synthetic-org", repo: "synthetic-repo" }],
    ["assign", { owner: "synthetic-org", repo: "synthetic-repo", issue_number: 123,
      assignees: ["synthetic-owner"] }],
  ]);
  console.log("github-script v9 compatibility passed; exact workflow body, REST mocked");
};
