import json
from pathlib import Path
import pytest
from models import Board, BoardItem, Prompt, Version
from storage import Storage
from library_export import write_library_export


@pytest.fixture
def store(tmp_path):
    s = Storage(tmp_path/'library')
    p = Prompt('p','Grüße','','Vorhandener Text',versions=[Version('v','p',1,'Version','Inhalt')])
    s.save_prompts([p])
    s.save_boards([Board('b','Übersicht',items=[BoardItem('i','b','p','v')])])
    return s


def mutate(s, action):
    p = Prompt('new','Neu','','Text')
    v = Version('v','p',2,'Neu','Text')
    return {
        'upsert_prompt':lambda:s.upsert_prompt(p),
        'delete_prompt':lambda:s.delete_prompt('p'),
        'add_version':lambda:s.add_version('p',v),
        'upsert_version':lambda:s.upsert_version('p',v),
        'delete_version':lambda:s.delete_version('p','v'),
        'save_prompts':lambda:s.save_prompts([p]),
        'upsert_board':lambda:s.upsert_board(Board('new','Neu')),
        'delete_board':lambda:s.delete_board('b'),
        'add_item_to_board':lambda:s.add_item_to_board('b','new'),
        'save_boards':lambda:s.save_boards([]),
        'remove_item_from_board':lambda:s.remove_item_from_board('b','p','v'),
    }[action]()


PROMPT_ACTIONS = ['upsert_prompt','delete_prompt','add_version','upsert_version','delete_version','save_prompts']
BOARD_ACTIONS = ['upsert_board','delete_board','add_item_to_board','save_boards','remove_item_from_board']


@pytest.mark.parametrize('action',PROMPT_ACTIONS+BOARD_ACTIONS)
@pytest.mark.parametrize('failure',['permission','missing','utf8','json'])
def test_mutation_keeps_both_files_on_failed_load(store,monkeypatch,action,failure):
    target=store.prompts_file if action in PROMPT_ACTIONS else store.boards_file
    if failure=='utf8':target.write_bytes(b'\xffunreadable')
    elif failure=='json':target.write_bytes(b'{"incomplete":')
    before={f:f.read_bytes() for f in (store.prompts_file,store.boards_file)}
    original=Path.read_text
    if failure in ('permission','missing'):
        error=PermissionError if failure=='permission' else FileNotFoundError
        def read(path,*args,**kwargs):
            if path==target:raise error('synthetic library read failure')
            return original(path,*args,**kwargs)
        monkeypatch.setattr(Path,'read_text',read)
    with pytest.raises(OSError):mutate(store,action)
    assert {f:f.read_bytes() for f in before}==before


@pytest.mark.parametrize('action',['delete_prompt','delete_version'])
def test_delete_preflights_boards_before_writing_prompts(store,action):
    store.boards_file.write_bytes(b'{broken board data')
    before=[f.read_bytes() for f in (store.prompts_file,store.boards_file)]
    with pytest.raises(OSError):mutate(store,action)
    assert [f.read_bytes() for f in (store.prompts_file,store.boards_file)]==before


@pytest.mark.parametrize('key,value',[('prompts',None),('prompts',{}),('prompts',[None]),('prompts',[{'id':'p','versions':['unparsed version']}]),('prompts',[{'id':'p','versions':{}}]),('boards',None),('boards',[{'id':'b','items':['unparsed item']}]),('boards',[{'id':'b','items':{}}])])
def test_malformed_structure_is_not_silently_discarded(store,key,value):
    target=store.prompts_file if key=='prompts' else store.boards_file
    target.write_text(json.dumps({key:value}),encoding='utf-8')
    before=target.read_bytes()
    with pytest.raises(OSError):mutate(store,'upsert_prompt' if key=='prompts' else 'upsert_board')
    assert target.read_bytes()==before


@pytest.mark.parametrize('key',['prompts','boards'])
def test_export_keeps_previous_backup_when_library_is_unreadable(store,tmp_path,key):
    target=store.prompts_file if key=='prompts' else store.boards_file
    target.write_bytes(b'not valid JSON')
    backup=tmp_path/'backup.json'
    backup.write_bytes(b'previous backup')
    with pytest.raises(OSError):write_library_export(store,backup)
    assert backup.read_bytes()==b'previous backup'


def test_missing_file_after_creation_is_not_recreated_by_save(store):
    store.prompts_file.unlink()
    with pytest.raises(OSError):mutate(store,'upsert_prompt')
    assert not store.prompts_file.exists()


def test_normal_mutations_keep_existing_entries_and_cleanup_references(store):
    mutate(store,'upsert_prompt')
    assert {p.id for p in store.load_prompts()}=={'p','new'}
    mutate(store,'delete_version')
    assert store.get_prompt('p').versions==[]
    assert store.load_boards()[0].items==[]
    assert store.remove_item_from_board('b','missing') is False


def test_recovery_requires_repaired_source_and_succeeds_without_restart(store):
    old=store.prompts_file.read_bytes()
    store.prompts_file.write_bytes(b'{damaged')
    with pytest.raises(OSError):mutate(store,'upsert_prompt')
    assert store.prompts_file.read_bytes()==b'{damaged'
    store.prompts_file.write_bytes(old)
    mutate(store,'upsert_prompt')
    assert {p.id for p in store.load_prompts()}=={'p','new'}


@pytest.mark.parametrize('action',['delete_prompt','delete_version'])
def test_delete_uses_one_preflight_snapshot_for_boards(store,monkeypatch,action):
    original=Path.read_text
    reads=[]
    def read(path,*args,**kwargs):
        if path==store.boards_file:
            reads.append(path)
            if len(reads)>1:raise PermissionError('second board read failed')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',read)
    mutate(store,action)
    assert len(reads)==1
    assert json.loads(store.boards_file.read_bytes())['boards'][0]['items']==[]


def test_pdf_export_does_not_render_an_unreadable_library(store,tmp_path,monkeypatch):
    import pdf_exporter
    store.prompts_file.write_bytes(b'{invalid')
    destination=tmp_path/'backup.pdf'
    destination.write_bytes(b'%PDF-previous')
    def render(*args,**kwargs):raise AssertionError('renderer must not run')
    monkeypatch.setattr(pdf_exporter,'_safe_export_html_to_pdf',render)
    with pytest.raises(OSError):pdf_exporter.export_all_prompts(store,None,str(destination))
    assert destination.read_bytes()==b'%PDF-previous'


def test_same_storage_object_serializes_parallel_updates(store):
    from concurrent.futures import ThreadPoolExecutor
    def insert(index):store.upsert_prompt(Prompt(str(index),'Titel','','Text'))
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(insert,range(12)))
    assert {p.id for p in store.load_prompts()}=={'p',*map(str,range(12))}


@pytest.mark.parametrize('mode',['prompt-new','prompt-edit','version-new','version-edit'])
def test_dialog_stays_open_without_mutating_shared_models_on_read_failure(store,qapp,monkeypatch,mode):
    from dataclasses import asdict
    from PySide6 import QtWidgets
    from prompt_dialog import PromptDialog,VersionDialog
    p=store.get_prompt('p')
    before=asdict(p)
    if mode.startswith('prompt'):
        dialog=PromptDialog(store,p if mode.endswith('edit') else None)
        label='Speichern'
    else:
        dialog=VersionDialog(store,p,p.versions[0] if mode.endswith('edit') else None)
        label='Speichern' if mode.endswith('edit') else 'Version erstellen'
    button=next(b for b in dialog.findChildren(QtWidgets.QPushButton) if b.text()==label)
    dialog.title_edit.setText('Neue Grüße')
    dialog.text_edit.setPlainText('Geänderter Text')
    messages=[]
    accepted=[]
    monkeypatch.setattr(QtWidgets.QMessageBox,'critical',lambda *args:messages.append(args))
    dialog.accepted.connect(lambda:accepted.append(True))
    store.prompts_file.write_bytes(b'{unreadable original')
    dialog.show()
    try:
        button.click()
        assert dialog.isVisible()
        assert dialog.title_edit.text()=='Neue Grüße'
        assert accepted==[] and len(messages)==1
        assert asdict(p)==before
        assert store.prompts_file.read_bytes()==b'{unreadable original'
    finally:dialog.close()


@pytest.mark.parametrize('edit',[False,True])
def test_version_dialog_does_not_accept_when_prompt_was_deleted(store,qapp,monkeypatch,edit):
    from PySide6 import QtWidgets
    from prompt_dialog import VersionDialog
    p=store.get_prompt('p')
    dialog=VersionDialog(store,p,p.versions[0] if edit else None)
    dialog.title_edit.setText('Neue Version')
    dialog.text_edit.setPlainText('Text')
    store.delete_prompt('p')
    messages=[]
    monkeypatch.setattr(QtWidgets.QMessageBox,'warning',lambda *args:messages.append(args))
    (dialog._on_save_update if edit else dialog._on_save_create)()
    assert dialog.result()!=QtWidgets.QDialog.DialogCode.Accepted
    assert len(messages)==1
    assert store.load_prompts()==[]
    dialog.close()


def test_supported_null_placeholders_do_not_block_legacy_library(store):
    data=json.loads(store.prompts_file.read_bytes())
    data['prompts'][0]['versions'].insert(0,None)
    store.prompts_file.write_text(json.dumps(data),encoding='utf-8')
    mutate(store,'upsert_prompt')
    existing=store.get_prompt('p')
    assert existing.text=='Vorhandener Text'
    assert existing.versions[0].text=='Inhalt'
    assert {p.id for p in store.load_prompts()}=={'p','new'}


@pytest.mark.parametrize('mode',['prompt-new','prompt-edit','version-new','version-edit'])
def test_save_buttons_commit_and_accept_on_healthy_library(store,qapp,mode):
    from PySide6 import QtWidgets
    from prompt_dialog import PromptDialog,VersionDialog
    p=store.get_prompt('p')
    if mode.startswith('prompt'):
        dialog=PromptDialog(store,p if mode.endswith('edit') else None)
        label='Speichern'
    else:
        dialog=VersionDialog(store,p,p.versions[0] if mode.endswith('edit') else None)
        label='Speichern' if mode.endswith('edit') else 'Version erstellen'
    dialog.title_edit.setText('Geänderte Grüße')
    dialog.text_edit.setPlainText('Gespeicherter Text')
    next(b for b in dialog.findChildren(QtWidgets.QPushButton) if b.text()==label).click()
    assert dialog.result()==QtWidgets.QDialog.DialogCode.Accepted
    if mode.startswith('prompt'):
        assert store.get_prompt(dialog.prompt.id).text=='Gespeicherter Text'
    else:
        assert any(v.text=='Gespeicherter Text' for v in store.get_prompt('p').versions)
    dialog.close()


@pytest.mark.parametrize('kind',['txt','pdf','json'])
@pytest.mark.parametrize('source',['prompts','boards'])
def test_mainwindow_exports_preserve_backups_and_report_read_errors(store,qapp,monkeypatch,tmp_path,kind,source):
    import profiprompt
    from profiprompt import MainWindow
    target=store.prompts_file if source=='prompts' else store.boards_file
    target.write_bytes(b'{damaged library')
    backup=tmp_path/f'backup.{kind}'
    backup.write_bytes(b'previous complete backup')
    errors=[]
    successes=[]
    monkeypatch.setattr(profiprompt.QFileDialog,'getSaveFileName',lambda *args,**kwargs:(str(backup),''))
    monkeypatch.setattr(profiprompt.QMessageBox,'critical',lambda *args,**kwargs:errors.append(args))
    monkeypatch.setattr(profiprompt.QMessageBox,'information',lambda *args,**kwargs:successes.append(args))
    window=MainWindow.__new__(MainWindow)
    window.storage=store
    window.settings=None
    action={'txt':MainWindow.export_all_txt,'pdf':MainWindow.export_all_pdf,'json':MainWindow.export_library_json}[kind]
    action(window)
    assert backup.read_bytes()==b'previous complete backup'
    assert len(errors)==1 and successes==[]
