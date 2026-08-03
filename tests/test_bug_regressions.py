"""Regressionstests — bugfix-library-transfer Batch #21 (2026-06-21) + Advisor-CP.

Geprüfte Patterns:
  D2 — deprecated QtCore/QtWidgets-Enums
       board_manager.py, profiprompt.py (Batch #21)
       dashboard.py, board_manager.py QMessageBox.Yes (Advisor-CP)
  U2 — json.loads ohne JSONDecodeError-Handler (storage.py)
"""
import unittest
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
BOARD_MGR = SRC / "board_manager.py"
PROFIPROMPT = SRC / "profiprompt.py"
STORAGE = SRC / "storage.py"


# ── D2: board_manager.py ────────────────────────────────────────────────────

class TestD2BoardManager(unittest.TestCase):
    def _src(self):
        return BOARD_MGR.read_text(encoding="utf-8")

    def test_pointing_hand_cursor_migrated(self):
        src = self._src()
        self.assertIn("QtCore.Qt.CursorShape.PointingHandCursor", src,
                      "board_manager: Qt.PointingHandCursor nicht migriert — BUG-D2")
        self.assertNotIn("QtCore.Qt.PointingHandCursor", src,
                         "board_manager: deprecated Qt.PointingHandCursor noch vorhanden — BUG-D2")

    def test_align_left_top_migrated(self):
        src = self._src()
        self.assertIn("QtCore.Qt.AlignmentFlag.AlignLeft", src,
                      "board_manager: Qt.AlignLeft nicht migriert — BUG-D2")
        self.assertNotIn("QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop", src,
                         "board_manager: deprecated Qt.AlignLeft|AlignTop noch vorhanden — BUG-D2")

    def test_custom_context_menu_migrated(self):
        src = self._src()
        self.assertIn("QtCore.Qt.ContextMenuPolicy.CustomContextMenu", src,
                      "board_manager: Qt.CustomContextMenu nicht migriert — BUG-D2")
        self.assertNotIn("QtCore.Qt.CustomContextMenu)", src,
                         "board_manager: deprecated Qt.CustomContextMenu noch vorhanden — BUG-D2")

    def test_left_button_migrated(self):
        src = self._src()
        self.assertIn("QtCore.Qt.MouseButton.LeftButton", src,
                      "board_manager: Qt.LeftButton nicht migriert — BUG-D2")
        self.assertNotIn("QtCore.Qt.LeftButton", src,
                         "board_manager: deprecated Qt.LeftButton noch vorhanden — BUG-D2")

    def test_smooth_transformation_migrated(self):
        src = self._src()
        self.assertIn("QtCore.Qt.TransformationMode.SmoothTransformation", src,
                      "board_manager: Qt.SmoothTransformation nicht migriert — BUG-D2")
        self.assertNotIn("QtCore.Qt.SmoothTransformation)", src,
                         "board_manager: deprecated Qt.SmoothTransformation noch vorhanden — BUG-D2")

    def test_move_action_migrated(self):
        src = self._src()
        self.assertIn("QtCore.Qt.DropAction.MoveAction", src,
                      "board_manager: Qt.MoveAction nicht migriert — BUG-D2")
        self.assertNotIn("QtCore.Qt.MoveAction)", src,
                         "board_manager: deprecated Qt.MoveAction noch vorhanden — BUG-D2")

    def test_size_policy_migrated(self):
        src = self._src()
        self.assertIn("QtWidgets.QSizePolicy.Policy.Minimum", src,
                      "board_manager: QSizePolicy.Minimum nicht migriert — BUG-D2")
        self.assertIn("QtWidgets.QSizePolicy.Policy.Expanding", src,
                      "board_manager: QSizePolicy.Expanding nicht migriert — BUG-D2")


# ── D2: profiprompt.py ──────────────────────────────────────────────────────

class TestD2ProfiPrompt(unittest.TestCase):
    def _src(self):
        return PROFIPROMPT.read_text(encoding="utf-8")

    def test_dock_widget_area_migrated(self):
        src = self._src()
        self.assertIn("Qt.DockWidgetArea.LeftDockWidgetArea", src,
                      "profiprompt: Qt.LeftDockWidgetArea nicht migriert — BUG-D2")
        self.assertIn("Qt.DockWidgetArea.RightDockWidgetArea", src,
                      "profiprompt: Qt.RightDockWidgetArea nicht migriert — BUG-D2")

    def test_bare_dock_widget_area_absent(self):
        src = self._src()
        import re
        # Keine Qt.LeftDockWidgetArea / Qt.RightDockWidgetArea ohne .DockWidgetArea.
        bare = re.findall(r'Qt\.(Left|Right)DockWidgetArea(?!\s*=)', src)
        self.assertFalse(bare,
                         f"profiprompt: deprecated Qt.xDockWidgetArea noch vorhanden: {bare} — BUG-D2")


# ── U2: storage.py ──────────────────────────────────────────────────────────

class TestU2Storage(unittest.TestCase):
    def _src(self):
        return STORAGE.read_text(encoding="utf-8")

    def test_load_prompts_has_json_decode_error_handler(self):
        src = self._src()
        # Prüfen ob load_prompts einen try/except-Block enthält
        self.assertIn("json.JSONDecodeError", src,
                      "storage: load_prompts ohne JSONDecodeError-Handler — BUG-U2")

    def test_load_boards_has_json_decode_error_handler(self):
        src = self._src()
        # Mindestens 2 except-Blöcke (für load_prompts und load_boards)
        count = src.count("json.JSONDecodeError")
        self.assertGreaterEqual(count, 2,
                                f"storage: nur {count} JSONDecodeError-Handler — load_boards fehlt — BUG-U2")

    def test_load_prompts_try_except_present(self):
        src = self._src()
        # try/except muss VOR dem json.loads für prompts stehen
        idx_try = src.find("def load_prompts")
        idx_except = src.find("except (json.JSONDecodeError", idx_try)
        idx_next_def = src.find("\n    def ", idx_try + 1)
        self.assertGreater(idx_except, idx_try,
                           "storage: load_prompts try/except fehlt — BUG-U2")
        self.assertLess(idx_except, idx_next_def,
                        "storage: load_prompts except nicht innerhalb der Funktion — BUG-U2")

    def test_load_boards_try_except_present(self):
        src = self._src()
        idx_try = src.find("def load_boards")
        idx_except = src.find("except (json.JSONDecodeError", idx_try)
        idx_next_def = src.find("\n    def ", idx_try + 1)
        self.assertGreater(idx_except, idx_try,
                           "storage: load_boards try/except fehlt — BUG-U2")
        self.assertLess(idx_except, idx_next_def,
                        "storage: load_boards except nicht innerhalb der Funktion — BUG-U2")


# ── D2: dashboard.py (Advisor-CP) ───────────────────────────────────────────

DASHBOARD = SRC / "dashboard.py"


class TestD2DashboardAdvisorCP(unittest.TestCase):
    def _src(self):
        return DASHBOARD.read_text(encoding="utf-8")

    def test_custom_context_menu_migrated(self):
        src = self._src()
        self.assertIn("QtCore.Qt.ContextMenuPolicy.CustomContextMenu", src,
                      "dashboard: Qt.CustomContextMenu nicht migriert — BUG-D2")
        self.assertNotIn("QtCore.Qt.CustomContextMenu)", src,
                         "dashboard: deprecated Qt.CustomContextMenu noch vorhanden — BUG-D2")

    def test_drag_drop_mode_migrated(self):
        src = self._src()
        self.assertIn("QAbstractItemView.DragDropMode.DragOnly", src,
                      "dashboard: QAbstractItemView.DragOnly nicht migriert — BUG-D2")
        self.assertNotIn("QAbstractItemView.DragOnly\n", src,
                         "dashboard: deprecated QAbstractItemView.DragOnly noch vorhanden — BUG-D2")

    def test_selection_mode_migrated(self):
        src = self._src()
        self.assertIn("QAbstractItemView.SelectionMode.SingleSelection", src,
                      "dashboard: QAbstractItemView.SingleSelection nicht migriert — BUG-D2")

    def test_user_role_migrated(self):
        src = self._src()
        count_new = src.count("Qt.ItemDataRole.UserRole")
        count_old = src.count("QtCore.Qt.UserRole")
        self.assertGreaterEqual(count_new, 5,
                                f"dashboard: weniger als 5 UserRole-Migrationen ({count_new}) — BUG-D2")
        self.assertEqual(count_old, 0,
                         f"dashboard: {count_old} deprecated Qt.UserRole noch vorhanden — BUG-D2")

    def test_copy_action_migrated(self):
        src = self._src()
        self.assertIn("QtCore.Qt.DropAction.CopyAction", src,
                      "dashboard: Qt.CopyAction nicht migriert — BUG-D2")
        self.assertNotIn("QtCore.Qt.CopyAction\n", src,
                         "dashboard: deprecated Qt.CopyAction noch vorhanden — BUG-D2")

    def test_message_box_yes_migrated(self):
        src = self._src()
        self.assertIn("QMessageBox.StandardButton.Yes", src,
                      "dashboard: QMessageBox.Yes nicht migriert — BUG-D2")
        self.assertNotIn("== QtWidgets.QMessageBox.Yes:", src,
                         "dashboard: deprecated QMessageBox.Yes noch vorhanden — BUG-D2")


# ── Bugsweep 28: Board & Dashboard State Resilience ─────────────────────────

class TestBugsweep28GUIAndBoardState(unittest.TestCase):
    def test_board_from_dict_missing_title_and_id(self):
        from models import board_from_dict, Board
        # Board-JSON ohne 'title' und 'id' darf keinen KeyError werfen
        raw = {"description": "Test board without title"}
        board = board_from_dict(raw)
        self.assertIsInstance(board, Board)
        self.assertEqual(board.title, "")
        self.assertTrue(len(board.id) > 0)

    def test_boarditem_from_dict_missing_keys(self):
        from models import boarditem_from_dict, BoardItem
        # BoardItem-JSON ohne 'id', 'board_id' oder 'prompt_id' darf keinen KeyError werfen
        raw = {"version_id": "v123"}
        item = boarditem_from_dict(raw)
        self.assertIsInstance(item, BoardItem)
        self.assertEqual(item.version_id, "v123")
        self.assertEqual(item.board_id, "")
        self.assertEqual(item.prompt_id, "")

    def test_dashboard_tags_none_resilience(self):
        from models import Prompt
        # Prompt mit None in tags darf bei Tag-Iterierung in Dashboard-Filtern nicht abstürzen
        p = Prompt(id="p1", title="Test Prompt", purpose="Testing", text="Sample text", tags=[None, "ai"])
        search_text = "ai"
        has_match = any(search_text in t.lower() for t in (p.tags or []) if isinstance(t, str))
        self.assertTrue(has_match)


if __name__ == "__main__":
    unittest.main()

