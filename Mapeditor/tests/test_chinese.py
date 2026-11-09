import re

from PySide6.QtWidgets import QDialogButtonBox

from mapeditor import ansicht, i18n
from mapeditor.document import Document
from mapeditor.i18n import lade_regeln, lade_tabelle, meldung, setze_sprache, tr, trn
from mapeditor.project import Project
from mapeditor.race_parameters import RaceParametersDialog
from mapeditor.ux import choice_text, choice_value, edit_text, zahl
from mapeditor.window import MainWindow, german_numbers, lap_text, parse_value


def test_all_chinese_resources_and_placeholders():
    for path in (i18n.TABELLE, i18n.MELDUNGEN, i18n.REGELN):
        for row in lade_tabelle(path):
            assert row['zh'].strip(), row
            for en, zh in zip(row['en'].split('|'), row['zh'].split('|')):
                assert i18n.platzhalter(en) == i18n.platzhalter(zh), row['en']
                source = re.findall(r'\{(\d*)\}', en)
                target = re.findall(r'\{(\d*)\}', zh)
                # Numbered replacements may reorder sentence constituents.
                assert len(source) == len(target), row['en']
                assert all(not x or 1 <= int(x) <= len(source) for x in target), row['en']
            assert row['en'].count('|') == row['zh'].count('|')


def test_chinese_lookup_plural_data_words_and_messages(app):
    setze_sprache('zh')
    assert tr('Save') == '保存'
    assert tr('Track race parameters') == '赛道比赛参数'
    assert choice_text('links') == tr('left')
    assert choice_value('richtung', choice_text('links')) == 'links'
    assert parse_value('是', False, 'aktiv') is True
    assert parse_value('否', True, 'aktiv') is False
    row = next(r for r in lade_tabelle() if '|' in r['en'])
    singular, plural = row['en'].split('|', 1)
    assert trn(2, singular, plural) == row['zh'].split('|', 1)[1].format(n=2)
    assert meldung('ERS harvest limit must be between 0 and 1000 MJ') == 'ERS 回收上限必须介于 0 和 1000 MJ 之间'
    assert meldung('Track edge outside X/Z ±100 m at 7 stations (including offset 3)') == '赛道边缘在 7 个位置超出 X/Z ±100 m（含偏移 3）'
    rule = lade_regeln()[0]
    assert i18n.rule_title(rule['id']) == rule['zh']
    help_text = i18n.html('hilfe')
    assert all(word in help_text for word in ('回放摄像机', '从游戏加载赛道', '赛道比赛参数'))


def test_chinese_numbers_panel_and_standard_buttons(app):
    setze_sprache('zh')
    assert i18n.qlocale().name() == 'zh_CN'
    assert i18n.dezimal('1.5') == '1.5'
    assert edit_text(1.5) == '1.5'
    assert german_numbers('989.0 m') == '989.0 m'
    assert lap_text(104.7) == '1:44.7'
    assert '1.5' in zahl(1.5)
    dialog = RaceParametersDialog(Document(Project()))
    check, spin = dialog.harvest['HarvestLimitMGUK']
    check.setChecked(True)
    spin.setValue(7.5)
    assert spin.text() == '7.500 MJ'
    assert dialog.windowTitle() == '赛道比赛参数'
    assert '取消' in dialog.buttons.button(QDialogButtonBox.Cancel).text()


def test_language_switching_restores_english_and_german(app):
    window = MainWindow(Project())
    for code, label in [('zh', '保存'), ('en', 'Save'), ('de', 'Speichern'), ('zh', '保存')]:
        window.retranslate(code)
        assert tr('Save') == label
        panel = RaceParametersDialog(window.document)
        assert panel.windowTitle() == tr('Track race parameters')
        panel.close()
    ansicht.save_language('zh')
    assert ansicht.load_language() == 'zh'
    setze_sprache('en')
    assert meldung('Line needs at least 2 points') == 'Line needs at least 2 points'
    setze_sprache('de')
    assert meldung('Line needs at least 2 points') == 'Linie braucht mindestens 2 Punkte'
