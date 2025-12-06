"""Tests for CLI commands."""

import pytest
import sys
import tempfile
import yaml
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from argparse import Namespace

from localization_analyzer.cli import (
    cmd_init,
    cmd_analyze,
    cmd_fix,
    cmd_missing,
    cmd_validate,
    cmd_stats,
    cmd_diff,
    cmd_sync,
    cmd_lang,
    cmd_discover,
    cmd_translate,
    load_and_validate_config,
    main,
)
from localization_analyzer.utils.config import ConfigValidationError


class TestCmdInit:
    """Test cases for cmd_init command."""

    def test_init_creates_config_file(self):
        """init komutu başarıyla config dosyası oluşturmalı."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('localization_analyzer.cli.Path.cwd', return_value=Path(tmpdir)):
                args = Namespace(framework='swift', force=False)
                result = cmd_init(args)

                assert result == 0
                config_path = Path(tmpdir) / '.localization.yml'
                assert config_path.exists()

                # Config içeriğini kontrol et
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                assert config_data['project']['framework'] == 'swift'

    def test_init_fails_without_force_if_exists(self):
        """Config dosyası varsa --force olmadan hata vermeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Önce config dosyası oluştur
            config_path = Path(tmpdir) / '.localization.yml'
            config_path.write_text('existing: config')

            with patch('localization_analyzer.cli.Path.cwd', return_value=Path(tmpdir)):
                args = Namespace(framework='swift', force=False)
                result = cmd_init(args)

                assert result == 1

    def test_init_overwrites_with_force(self):
        """--force flag ile mevcut config üzerine yazılmalı."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / '.localization.yml'
            config_path.write_text('old: config')

            with patch('localization_analyzer.cli.Path.cwd', return_value=Path(tmpdir)):
                args = Namespace(framework='swift', force=True)
                result = cmd_init(args)

                assert result == 0
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                assert 'old' not in config_data

    def test_init_with_different_frameworks(self):
        """Farklı framework'ler için config oluşturulabilmeli."""
        frameworks = ['swift', 'react', 'flutter', 'android']

        for framework in frameworks:
            with tempfile.TemporaryDirectory() as tmpdir:
                with patch('localization_analyzer.cli.Path.cwd', return_value=Path(tmpdir)):
                    args = Namespace(framework=framework, force=False)
                    result = cmd_init(args)

                    assert result == 0
                    config_path = Path(tmpdir) / '.localization.yml'
                    with open(config_path, 'r') as f:
                        config_data = yaml.safe_load(f)
                    assert config_data['project']['framework'] == framework


class TestCmdAnalyze:
    """Test cases for cmd_analyze command."""

    @patch('localization_analyzer.cli.LocalizationAnalyzer')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_analyze_basic(self, mock_load_config, mock_analyzer_class):
        """Analyze komutu temel senaryoda başarıyla çalışmalı."""
        # Mock config
        mock_config = MagicMock()
        mock_config.project.framework = 'swift'
        mock_config.paths.source = '.'
        mock_config.reports.formats = []
        mock_load_config.return_value = mock_config

        # Mock analyzer
        mock_analyzer = MagicMock()
        mock_result = MagicMock()
        mock_result.health.score = 85
        mock_analyzer.analyze.return_value = mock_result
        mock_analyzer_class.return_value = mock_analyzer

        args = Namespace(
            framework=None,
            verbose=False,
            quiet=False,
            no_threads=False,
            json=None,
            html=None,
            serve=False,
            port=None,
            no_browser=False,
            edit=False,
            fail_below=None
        )

        result = cmd_analyze(args)

        assert result == 0
        mock_analyzer.analyze.assert_called_once()

    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_analyze_config_validation_error(self, mock_load_config):
        """Config validation hatası durumunda 1 dönmeli."""
        mock_load_config.side_effect = ConfigValidationError(['Config error'])

        args = Namespace(
            framework=None,
            verbose=False,
            quiet=False,
            no_threads=False,
            json=None,
            html=None,
            serve=False,
            port=None,
            no_browser=False,
            edit=False,
            fail_below=None
        )

        result = cmd_analyze(args)
        assert result == 1

    @patch('localization_analyzer.cli.LocalizationAnalyzer')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_analyze_fails_below_threshold(self, mock_load_config, mock_analyzer_class):
        """Health score threshold'un altındaysa 1 dönmeli."""
        mock_config = MagicMock()
        mock_config.project.framework = 'swift'
        mock_config.paths.source = '.'
        mock_config.reports.formats = []
        mock_load_config.return_value = mock_config

        mock_analyzer = MagicMock()
        mock_result = MagicMock()
        mock_result.health.score = 60  # Threshold 80
        mock_analyzer.analyze.return_value = mock_result
        mock_analyzer_class.return_value = mock_analyzer

        args = Namespace(
            framework=None,
            verbose=False,
            quiet=False,
            no_threads=False,
            json=None,
            html=None,
            serve=False,
            port=None,
            no_browser=False,
            edit=False,
            fail_below=80
        )

        result = cmd_analyze(args)
        assert result == 1

    @patch('localization_analyzer.cli.JSONReporter')
    @patch('localization_analyzer.cli.LocalizationAnalyzer')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_analyze_with_json_output(self, mock_load_config, mock_analyzer_class, mock_json_reporter):
        """JSON rapor oluşturulmalı."""
        mock_config = MagicMock()
        mock_config.project.framework = 'swift'
        mock_config.paths.source = '.'
        mock_config.reports.formats = []
        mock_load_config.return_value = mock_config

        mock_analyzer = MagicMock()
        mock_result = MagicMock()
        mock_result.health.score = 85
        mock_analyzer.analyze.return_value = mock_result
        mock_analyzer_class.return_value = mock_analyzer

        args = Namespace(
            framework=None,
            verbose=False,
            quiet=False,
            no_threads=False,
            json='report.json',
            html=None,
            serve=False,
            port=None,
            no_browser=False,
            edit=False,
            fail_below=None
        )

        result = cmd_analyze(args)

        assert result == 0
        mock_json_reporter.generate.assert_called_once()

    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_analyze_unsupported_framework(self, mock_load_config):
        """Desteklenmeyen framework için hata vermeli."""
        mock_config = MagicMock()
        mock_config.project.framework = 'unsupported'
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        args = Namespace(
            framework='unsupported',
            verbose=False,
            quiet=False,
            no_threads=False,
            json=None,
            html=None,
            serve=False,
            port=None,
            no_browser=False,
            edit=False,
            fail_below=None
        )

        result = cmd_analyze(args)
        assert result == 1


class TestCmdFix:
    """Test cases for cmd_fix command."""

    @patch('localization_analyzer.cli.AutoFixer')
    @patch('localization_analyzer.cli.create_backup')
    @patch('localization_analyzer.cli.LocalizationAnalyzer')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_fix_basic(self, mock_load_config, mock_analyzer_class, mock_backup, mock_fixer_class):
        """Fix komutu hardcoded string'leri düzeltmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        # Mock analyzer results
        mock_analyzer = MagicMock()
        mock_result = MagicMock()
        mock_hardcoded = MagicMock()
        mock_hardcoded.priority = 8
        mock_hardcoded.file = 'test.swift'
        mock_hardcoded.line = 10
        mock_hardcoded.text = 'Hello'
        mock_hardcoded.component = 'Text'
        mock_hardcoded.suggested_key = 'hello'
        mock_result.hardcoded_strings = [mock_hardcoded]
        mock_analyzer.analyze.return_value = mock_result
        mock_analyzer_class.return_value = mock_analyzer

        # Mock fixer
        mock_fixer = MagicMock()
        mock_fixer_class.return_value = mock_fixer

        args = Namespace(
            min_priority=8,
            dry_run=False,
            no_backup=False
        )

        result = cmd_fix(args)

        assert result == 0
        mock_fixer.fix_hardcoded_string.assert_called_once()
        mock_fixer.print_summary.assert_called_once()

    @patch('localization_analyzer.cli.AutoFixer')
    @patch('localization_analyzer.cli.LocalizationAnalyzer')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_fix_dry_run(self, mock_load_config, mock_analyzer_class, mock_fixer_class):
        """Dry-run modunda backup oluşturmamalı."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_analyzer = MagicMock()
        mock_result = MagicMock()
        mock_result.hardcoded_strings = []
        mock_analyzer.analyze.return_value = mock_result
        mock_analyzer_class.return_value = mock_analyzer

        mock_fixer = MagicMock()
        mock_fixer_class.return_value = mock_fixer

        args = Namespace(
            min_priority=8,
            dry_run=True,
            no_backup=False
        )

        with patch('localization_analyzer.cli.create_backup') as mock_backup:
            result = cmd_fix(args)

            assert result == 0
            mock_backup.assert_not_called()

    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_fix_config_error(self, mock_load_config):
        """Config hatası durumunda 1 dönmeli."""
        mock_load_config.side_effect = ConfigValidationError(['Error'])

        args = Namespace(min_priority=8, dry_run=False, no_backup=False)
        result = cmd_fix(args)
        assert result == 1


class TestCmdMissing:
    """Test cases for cmd_missing command."""

    @patch('localization_analyzer.cli.MissingKeysFixer')
    @patch('localization_analyzer.cli.LocalizationAnalyzer')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_missing_no_keys(self, mock_load_config, mock_analyzer_class, mock_fixer_class):
        """Eksik key yoksa başarı mesajı göstermeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_analyzer = MagicMock()
        mock_result = MagicMock()
        mock_result.missing_keys = {}
        mock_analyzer.analyze.return_value = mock_result
        mock_analyzer_class.return_value = mock_analyzer

        args = Namespace(
            fix=False,
            report=None,
            auto=False,
            dry_run=False,
            no_backup=False
        )

        result = cmd_missing(args)
        assert result == 0

    @patch('localization_analyzer.cli.MissingKeysFixer')
    @patch('localization_analyzer.cli.create_backup')
    @patch('localization_analyzer.cli.LocalizationAnalyzer')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_missing_with_fix(self, mock_load_config, mock_analyzer_class, mock_backup, mock_fixer_class):
        """--fix flag ile eksik key'ler eklenmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_analyzer = MagicMock()
        mock_result = MagicMock()
        mock_result.missing_keys = {'key1': ['file1.swift']}
        mock_analyzer.analyze.return_value = mock_result
        mock_analyzer_class.return_value = mock_analyzer

        mock_fixer = MagicMock()
        mock_fixer_class.return_value = mock_fixer

        args = Namespace(
            fix=True,
            report=None,
            auto=False,
            dry_run=False,
            no_backup=False
        )

        result = cmd_missing(args)

        assert result == 0
        mock_fixer.fix_missing_keys.assert_called_once()

    @patch('localization_analyzer.cli.MissingKeysFixer')
    @patch('localization_analyzer.cli.LocalizationAnalyzer')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_missing_with_report(self, mock_load_config, mock_analyzer_class, mock_fixer_class):
        """--report flag ile rapor dosyası oluşturmalı."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_analyzer = MagicMock()
        mock_result = MagicMock()
        mock_result.missing_keys = {'key1': ['file1.swift']}
        mock_analyzer.analyze.return_value = mock_result
        mock_analyzer_class.return_value = mock_analyzer

        mock_fixer = MagicMock()
        mock_fixer_class.return_value = mock_fixer

        args = Namespace(
            fix=False,
            report='missing.md',
            auto=False,
            dry_run=False,
            no_backup=False
        )

        result = cmd_missing(args)

        assert result == 0
        mock_fixer.generate_missing_keys_report.assert_called_once()


class TestCmdValidate:
    """Test cases for cmd_validate command."""

    @patch('localization_analyzer.cli.LocalizationValidator')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_validate_success(self, mock_load_config, mock_file_manager_class, mock_validator_class):
        """Validation başarılı olmalı."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.languages = {}
        mock_file_manager_class.return_value = mock_file_manager

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.total_issues = 0
        mock_validator.validate_file.return_value = mock_result
        mock_validator_class.return_value = mock_validator

        args = Namespace(
            source='en',
            consistency=False,
            verbose=False
        )

        result = cmd_validate(args)
        assert result == 0

    @patch('localization_analyzer.cli.LocalizationValidator')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_validate_with_errors(self, mock_load_config, mock_file_manager_class, mock_validator_class):
        """Hata varsa 1 dönmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        # Mock file manager ile dosyalar
        mock_file_manager = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.exists.return_value = True
        mock_file_path.name = 'en.strings'
        mock_file_manager.languages = {
            'en': [mock_file_path]
        }
        mock_file_manager_class.return_value = mock_file_manager

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_error = MagicMock()
        mock_result.errors = [mock_error]
        mock_result.warnings = []
        mock_validator.validate_file.return_value = mock_result
        mock_validator_class.return_value = mock_validator

        args = Namespace(
            source='en',
            consistency=False,
            verbose=False
        )

        result = cmd_validate(args)
        assert result == 1

    @patch('localization_analyzer.cli.LocalizationValidator')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_validate_with_consistency(self, mock_load_config, mock_file_manager_class, mock_validator_class):
        """--consistency flag ile cross-language validation yapılmalı."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.languages = {
            'en': [Path('/tmp/en.strings')],
            'tr': [Path('/tmp/tr.strings')]
        }
        mock_file_manager.keys_by_language = {
            'en': {'key': 'value'}
        }
        mock_file_manager_class.return_value = mock_file_manager

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.total_issues = 0
        mock_validator.validate_file.return_value = mock_result
        mock_validator.validate_consistency.return_value = {'en': mock_result, 'tr': mock_result}
        mock_validator_class.return_value = mock_validator

        args = Namespace(
            source='en',
            consistency=True,
            verbose=False
        )

        result = cmd_validate(args)
        assert result == 0
        mock_validator.validate_consistency.assert_called_once()


class TestCmdStats:
    """Test cases for cmd_stats command."""

    @patch('localization_analyzer.cli.StatsCalculator')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_stats_basic(self, mock_load_config, mock_file_manager_class, mock_stats_class):
        """Stats komutu istatistikleri göstermeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_config.project.name = 'TestProject'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.keys_by_language = {'en': {'key': 'value'}}
        mock_file_manager_class.return_value = mock_file_manager

        mock_calculator = MagicMock()
        mock_stats = MagicMock()
        mock_stats.overall_completion = 90.0
        mock_calculator.calculate.return_value = mock_stats
        mock_stats_class.return_value = mock_calculator

        args = Namespace(
            source='en',
            json=None,
            markdown=None,
            missing=False,
            lang=None,
            ci=False,
            threshold=80.0
        )

        result = cmd_stats(args)
        assert result == 0
        mock_calculator.print_summary.assert_called_once()

    @patch('localization_analyzer.cli.StatsCalculator')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_stats_json_export(self, mock_load_config, mock_file_manager_class, mock_stats_class):
        """--json flag ile JSON export yapılmalı."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_config.project.name = 'TestProject'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.keys_by_language = {'en': {'key': 'value'}}
        mock_file_manager_class.return_value = mock_file_manager

        mock_calculator = MagicMock()
        mock_stats = MagicMock()
        mock_calculator.calculate.return_value = mock_stats
        mock_stats_class.return_value = mock_calculator

        args = Namespace(
            source='en',
            json='stats.json',
            markdown=None,
            missing=False,
            lang=None,
            ci=False,
            threshold=80.0
        )

        result = cmd_stats(args)
        assert result == 0
        mock_calculator.export_json.assert_called_once()

    @patch('localization_analyzer.cli.StatsCalculator')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_stats_markdown_export(self, mock_load_config, mock_file_manager_class, mock_stats_class):
        """--markdown flag ile Markdown export yapılmalı."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_config.project.name = 'TestProject'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.keys_by_language = {'en': {'key': 'value'}}
        mock_file_manager_class.return_value = mock_file_manager

        mock_calculator = MagicMock()
        mock_stats = MagicMock()
        mock_calculator.calculate.return_value = mock_stats
        mock_stats_class.return_value = mock_calculator

        args = Namespace(
            source='en',
            json=None,
            markdown='stats.md',
            missing=False,
            lang=None,
            ci=False,
            threshold=80.0
        )

        result = cmd_stats(args)
        assert result == 0
        mock_calculator.export_markdown.assert_called_once()


class TestCmdDiff:
    """Test cases for cmd_diff command."""

    @patch('localization_analyzer.cli.LocalizationDiff')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_diff_basic(self, mock_load_config, mock_file_manager_class, mock_diff_class):
        """Diff komutu iki dil arasındaki farkları göstermeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.keys_by_language = {
            'en': {'key1': 'Hello', 'key2': 'World'},
            'tr': {'key1': 'Merhaba'}
        }
        mock_file_manager_class.return_value = mock_file_manager

        mock_differ = MagicMock()
        mock_result = MagicMock()
        mock_result.removed = []
        mock_differ.compare.return_value = mock_result
        mock_diff_class.return_value = mock_differ

        args = Namespace(
            source='en',
            target='tr',
            output=None,
            format=None,
            untranslated=False,
            verbose=False,
            limit=50,
            fail_on_missing=False
        )

        result = cmd_diff(args)
        assert result == 0
        mock_differ.print_diff.assert_called_once()

    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_diff_source_not_found(self, mock_load_config, mock_file_manager_class):
        """Source dili bulunamazsa 1 dönmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.keys_by_language = {}
        mock_file_manager_class.return_value = mock_file_manager

        args = Namespace(
            source='en',
            target='tr',
            output=None,
            format=None,
            untranslated=False,
            verbose=False,
            limit=50,
            fail_on_missing=False
        )

        result = cmd_diff(args)
        assert result == 1

    @patch('localization_analyzer.cli.LocalizationDiff')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_diff_with_output(self, mock_load_config, mock_file_manager_class, mock_diff_class):
        """--output flag ile dosyaya export edilmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.keys_by_language = {
            'en': {'key': 'value'},
            'tr': {'key': 'değer'}
        }
        mock_file_manager_class.return_value = mock_file_manager

        mock_differ = MagicMock()
        mock_result = MagicMock()
        mock_result.removed = []
        mock_differ.compare.return_value = mock_result
        mock_diff_class.return_value = mock_differ

        args = Namespace(
            source='en',
            target='tr',
            output='diff.md',
            format='md',
            untranslated=False,
            verbose=False,
            limit=50,
            fail_on_missing=False
        )

        result = cmd_diff(args)
        assert result == 0
        mock_differ.export_diff.assert_called_once()


class TestCmdSync:
    """Test cases for cmd_sync command."""

    @patch('localization_analyzer.cli.LocalizationSync')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_sync_basic(self, mock_load_config, mock_file_manager_class, mock_sync_class):
        """Sync komutu dilleri senkronize etmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.keys_by_language = {
            'en': {'key1': 'Hello'},
            'tr': {}
        }
        mock_file_manager.languages = {
            'en': Path('/tmp/en.strings'),
            'tr': Path('/tmp/tr.strings')
        }
        mock_file_manager_class.return_value = mock_file_manager

        mock_syncer = MagicMock()
        mock_summary = MagicMock()
        mock_summary.has_changes = False
        mock_summary.total_failures = 0
        mock_syncer.sync_all.return_value = mock_summary
        mock_sync_class.return_value = mock_syncer

        args = Namespace(
            source='en',
            lang=None,
            translate=False,
            no_backup=False,
            dry_run=False,
            verbose=False,
            output=None,
            format=None,
            ci=False
        )

        result = cmd_sync(args)
        assert result == 0
        mock_syncer.sync_all.assert_called_once()

    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_sync_no_source_keys(self, mock_load_config, mock_file_manager_class):
        """Source key'ler yoksa 1 dönmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.keys_by_language = {}
        mock_file_manager_class.return_value = mock_file_manager

        args = Namespace(
            source='en',
            lang=None,
            translate=False,
            no_backup=False,
            dry_run=False,
            verbose=False,
            output=None,
            format=None,
            ci=False
        )

        result = cmd_sync(args)
        assert result == 1

    @patch('localization_analyzer.cli.LocalizationSync')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_sync_with_translate(self, mock_load_config, mock_file_manager_class, mock_sync_class):
        """--translate flag ile otomatik çeviri yapılmalı."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.keys_by_language = {'en': {'key': 'value'}}
        mock_file_manager.languages = {
            'en': Path('/tmp/en.strings'),
            'tr': Path('/tmp/tr.strings')
        }
        mock_file_manager_class.return_value = mock_file_manager

        mock_syncer = MagicMock()
        mock_summary = MagicMock()
        mock_summary.has_changes = False
        mock_summary.total_failures = 0
        mock_syncer.sync_all.return_value = mock_summary
        mock_sync_class.return_value = mock_syncer

        args = Namespace(
            source='en',
            lang=None,
            translate=True,
            no_backup=False,
            dry_run=False,
            verbose=False,
            output=None,
            format=None,
            ci=False
        )

        result = cmd_sync(args)
        assert result == 0
        # auto_translate=True ile çağrılmalı
        assert mock_sync_class.call_args[1]['auto_translate'] == True


class TestCmdLang:
    """Test cases for cmd_lang command."""

    @patch('localization_analyzer.cli.LanguageManager')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_lang_list(self, mock_load_config, mock_file_manager_class, mock_lang_manager_class):
        """--list flag ile diller listelenmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager_class.return_value = mock_file_manager

        mock_lang_manager = MagicMock()
        mock_lang_manager.list_languages.return_value = [
            {
                'code': 'en',
                'name': 'English',
                'exists': True,
                'key_count': 10,
                'missing_keys': 0,
                'completion': 100.0
            }
        ]
        mock_lang_manager_class.return_value = mock_lang_manager

        args = Namespace(
            list=True,
            add=None,
            remove=None,
            sync=None,
            source='en',
            empty=False,
            translate=False,
            dry_run=False,
            confirm=False
        )

        result = cmd_lang(args)
        assert result == 0
        mock_lang_manager.list_languages.assert_called_once()

    @patch('localization_analyzer.cli.LanguageManager')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_lang_add(self, mock_load_config, mock_file_manager_class, mock_lang_manager_class):
        """--add flag ile dil eklenmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager_class.return_value = mock_file_manager

        mock_lang_manager = MagicMock()
        mock_lang_manager.add_language.return_value = True
        mock_lang_manager_class.return_value = mock_lang_manager

        args = Namespace(
            list=False,
            add='de',
            remove=None,
            sync=None,
            source='en',
            empty=False,
            translate=False,
            dry_run=False,
            confirm=False
        )

        result = cmd_lang(args)
        assert result == 0
        mock_lang_manager.add_language.assert_called_once()

    @patch('localization_analyzer.cli.LanguageManager')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_lang_remove(self, mock_load_config, mock_file_manager_class, mock_lang_manager_class):
        """--remove flag ile dil silinmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager_class.return_value = mock_file_manager

        mock_lang_manager = MagicMock()
        mock_lang_manager.remove_language.return_value = True
        mock_lang_manager_class.return_value = mock_lang_manager

        args = Namespace(
            list=False,
            add=None,
            remove='de',
            sync=None,
            source='en',
            empty=False,
            translate=False,
            dry_run=False,
            confirm=True
        )

        result = cmd_lang(args)
        assert result == 0
        mock_lang_manager.remove_language.assert_called_once()

    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_lang_no_action(self, mock_load_config, mock_file_manager_class):
        """Action belirtilmezse 1 dönmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager_class.return_value = mock_file_manager

        args = Namespace(
            list=False,
            add=None,
            remove=None,
            sync=None,
            source='en',
            empty=False,
            translate=False,
            dry_run=False,
            confirm=False
        )

        result = cmd_lang(args)
        assert result == 1


class TestCmdDiscover:
    """Test cases for cmd_discover command."""

    @patch('localization_analyzer.cli.SwiftAdapter')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_discover_tables(self, mock_load_config, mock_adapter_class):
        """--tables flag ile .strings dosyaları keşfedilmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_adapter = MagicMock()
        mock_adapter.discover_tables.return_value = {
            'common': 'Common',
            'settings': 'Settings'
        }
        mock_adapter_class.return_value = mock_adapter

        args = Namespace(
            tables=True,
            modules=False,
            all=False,
            generate=False
        )

        result = cmd_discover(args)
        assert result == 0
        mock_adapter.discover_tables.assert_called_once()

    @patch('localization_analyzer.cli.SwiftAdapter')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_discover_modules(self, mock_load_config, mock_adapter_class):
        """--modules flag ile modül yapısı keşfedilmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_adapter = MagicMock()
        mock_adapter.auto_detect_module_mapping.return_value = {
            'Auth/*': 'auth',
            'Settings/*': 'settings'
        }
        mock_adapter_class.return_value = mock_adapter

        args = Namespace(
            tables=False,
            modules=True,
            all=False,
            generate=False
        )

        result = cmd_discover(args)
        assert result == 0
        mock_adapter.auto_detect_module_mapping.assert_called_once()

    @patch('localization_analyzer.cli.SwiftAdapter')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_discover_generate(self, mock_load_config, mock_adapter_class):
        """--generate flag ile config güncellenmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / '.localization.yml'

            # Mock config dosyası oluştur
            mock_config = MagicMock()
            mock_config.paths.source = '.'
            mock_config.l10n.tables = {}
            mock_config.l10n.module_mapping = {}
            mock_config.l10n.enabled = False
            mock_load_config.return_value = mock_config

            mock_adapter = MagicMock()
            mock_adapter.discover_tables.return_value = {'common': 'Common'}
            mock_adapter.auto_detect_module_mapping.return_value = {}
            mock_adapter_class.return_value = mock_adapter

            args = Namespace(
                tables=False,
                modules=False,
                all=False,
                generate=True
            )

            with patch('localization_analyzer.cli.Path.cwd', return_value=Path(tmpdir)):
                with patch.object(mock_config, 'save') as mock_save:
                    result = cmd_discover(args)

                    assert result == 0
                    mock_save.assert_called_once()


class TestCmdTranslate:
    """Test cases for cmd_translate command."""

    @patch('localization_analyzer.cli.TranslationService')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_translate_basic(self, mock_load_config, mock_file_manager_class, mock_translator_class):
        """Translate komutu çeviri yapmalı."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.languages = {'en': Path('/en'), 'tr': Path('/tr')}
        mock_file_manager.keys_by_language = {
            'en': {'greeting': 'Hello'}
        }
        mock_file_manager.keys = {}
        mock_file_manager_class.return_value = mock_file_manager

        mock_translator = MagicMock()
        mock_translator.translate.return_value = 'Merhaba'
        mock_translator_class.return_value = mock_translator

        args = Namespace(
            source='en',
            target='tr',
            key=None,
            force=False,
            dry_run=False,
            verbose=False
        )

        result = cmd_translate(args)
        assert result == 0
        mock_translator.translate.assert_called()

    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_translate_no_source_keys(self, mock_load_config, mock_file_manager_class):
        """Source key'ler yoksa 1 dönmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.languages = {'en': Path('/en')}
        mock_file_manager.keys_by_language = {}
        mock_file_manager_class.return_value = mock_file_manager

        args = Namespace(
            source='en',
            target='tr',
            key=None,
            force=False,
            dry_run=False,
            verbose=False
        )

        result = cmd_translate(args)
        assert result == 1

    @patch('localization_analyzer.cli.TranslationService')
    @patch('localization_analyzer.cli.LocalizationFileManager')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_translate_specific_key(self, mock_load_config, mock_file_manager_class, mock_translator_class):
        """--key flag ile spesifik key çevrilmeli."""
        mock_config = MagicMock()
        mock_config.paths.source = '.'
        mock_load_config.return_value = mock_config

        mock_file_manager = MagicMock()
        mock_file_manager.languages = {'en': Path('/en'), 'tr': Path('/tr')}
        mock_file_manager.keys_by_language = {
            'en': {'key1': 'Hello', 'key2': 'World'}
        }
        mock_file_manager.keys = {}
        mock_file_manager_class.return_value = mock_file_manager

        mock_translator = MagicMock()
        mock_translator.translate.return_value = 'Merhaba'
        mock_translator_class.return_value = mock_translator

        args = Namespace(
            source='en',
            target='tr',
            key='key1',
            force=False,
            dry_run=False,
            verbose=False
        )

        result = cmd_translate(args)
        assert result == 0
        # Sadece bir kez çağrılmalı (key1 için)
        assert mock_translator.translate.call_count == 1


class TestLoadAndValidateConfig:
    """Test cases for load_and_validate_config helper function."""

    @patch('localization_analyzer.cli.Config.from_file')
    def test_load_valid_config(self, mock_from_file):
        """Geçerli config yüklenmeli."""
        mock_config = MagicMock()
        mock_config.validate.return_value = ([], [])
        mock_from_file.return_value = mock_config

        config = load_and_validate_config(validate=True, verbose=False)

        assert config == mock_config
        mock_config.validate.assert_called_once()

    @patch('localization_analyzer.cli.Config.from_file')
    def test_load_config_with_warnings(self, mock_from_file):
        """Warning'ler verbose modda gösterilmeli."""
        mock_config = MagicMock()
        mock_config.validate.return_value = ([], ['Warning message'])
        mock_from_file.return_value = mock_config

        with patch('builtins.print') as mock_print:
            config = load_and_validate_config(validate=True, verbose=True)

            # Warning yazdırılmalı
            assert any('Warning message' in str(call) for call in mock_print.call_args_list)

    @patch('localization_analyzer.cli.Config.from_file')
    def test_load_config_with_errors(self, mock_from_file):
        """Hata varsa exception fırlatılmalı."""
        mock_config = MagicMock()
        mock_config.validate.return_value = (['Error message'], [])
        mock_from_file.return_value = mock_config

        with pytest.raises(ConfigValidationError):
            load_and_validate_config(validate=True, verbose=False)

    @patch('localization_analyzer.cli.Config.from_file')
    def test_load_without_validation(self, mock_from_file):
        """validate=False ise validation yapılmamalı."""
        mock_config = MagicMock()
        mock_from_file.return_value = mock_config

        config = load_and_validate_config(validate=False, verbose=False)

        assert config == mock_config
        mock_config.validate.assert_not_called()


class TestMainFunction:
    """Test cases for main() entry point."""

    @patch('sys.argv', ['localization-analyzer'])
    @patch('localization_analyzer.cli.argparse.ArgumentParser.print_help')
    def test_main_no_command(self, mock_help):
        """Komut belirtilmezse help gösterilmeli."""
        result = main()
        assert result == 0
        mock_help.assert_called_once()

    @patch('sys.argv', ['localization-analyzer', 'init', '--framework', 'swift'])
    def test_main_init_command(self):
        """init komutu çalışmalı."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('localization_analyzer.cli.Path.cwd', return_value=Path(tmpdir)):
                result = main()
                assert result == 0

    @patch('sys.argv', ['localization-analyzer', '--version'])
    def test_main_version(self):
        """--version flag çalışmalı."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        # argparse --version exits with 0
        assert exc_info.value.code == 0

    @patch('sys.argv', ['localization-analyzer', 'analyze'])
    @patch('localization_analyzer.cli.cmd_analyze')
    def test_main_analyze_command(self, mock_cmd_analyze):
        """analyze komutu delegate edilmeli."""
        mock_cmd_analyze.return_value = 0
        result = main()
        assert result == 0
        mock_cmd_analyze.assert_called_once()


class TestEdgeCases:
    """Edge case testleri."""

    @patch('localization_analyzer.cli.LocalizationAnalyzer')
    @patch('localization_analyzer.cli.load_and_validate_config')
    def test_analyze_empty_results(self, mock_load_config, mock_analyzer_class):
        """Boş analiz sonuçları handle edilmeli."""
        mock_config = MagicMock()
        mock_config.project.framework = 'swift'
        mock_config.paths.source = '.'
        mock_config.reports.formats = []
        mock_load_config.return_value = mock_config

        mock_analyzer = MagicMock()
        mock_result = MagicMock()
        mock_result.health.score = 100
        mock_result.hardcoded_strings = []
        mock_result.missing_keys = {}
        mock_analyzer.analyze.return_value = mock_result
        mock_analyzer_class.return_value = mock_analyzer

        args = Namespace(
            framework=None,
            verbose=False,
            quiet=False,
            no_threads=False,
            json=None,
            html=None,
            serve=False,
            port=None,
            no_browser=False,
            edit=False,
            fail_below=None
        )

        result = cmd_analyze(args)
        assert result == 0

    def test_init_with_invalid_directory_permissions(self):
        """Yazma izni olmayan dizinde hata handle edilmeli."""
        # Bu test sadece UNIX sistemlerde çalışır
        import platform
        if platform.system() == 'Windows':
            pytest.skip("Permission test not applicable on Windows")

        with tempfile.TemporaryDirectory() as tmpdir:
            readonly_dir = Path(tmpdir) / 'readonly'
            readonly_dir.mkdir()
            readonly_dir.chmod(0o444)  # Read-only

            try:
                with patch('localization_analyzer.cli.Path.cwd', return_value=readonly_dir):
                    args = Namespace(framework='swift', force=False)
                    # PermissionError beklenmeli ama yakalanmalı
                    try:
                        result = cmd_init(args)
                        # Eğer exception fırlatılmazsa
                    except PermissionError:
                        pass  # Beklenen davranış
            finally:
                readonly_dir.chmod(0o755)  # Cleanup için izni geri ver


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
