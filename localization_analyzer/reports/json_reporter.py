"""JSON report generator."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..core.analyzer import AnalysisResult
from ..core.file_manager import LocalizationFileManager
from ..frameworks.base import BaseAdapter
from ..utils.colors import Colors


class JSONReporter:
    """Generate JSON reports for analysis results."""

    @staticmethod
    def generate(
        result: AnalysisResult,
        file_manager: LocalizationFileManager,
        adapter: BaseAdapter,
        output_path: Optional[Path] = None,
        pretty: bool = True
    ) -> Path:
        """
        Generate JSON report.

        Args:
            result: Analysis result
            file_manager: File manager instance
            adapter: Framework adapter
            output_path: Output file path
            pretty: Pretty print JSON

        Returns:
            Path to generated report
        """
        if output_path is None:
            output_path = Path.cwd() / 'localization_report.json'

        # Build report structure
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'version': '1.0.0',
                'framework': adapter.__class__.__name__.replace('Adapter', '').lower(),
            },
            'health_score': {
                'score': result.health.score,
                'grade': result.health.grade,
                'localized_count': result.health.localized_count,
                'hardcoded_count': result.health.hardcoded_count,
                'total_strings': result.health.total_strings,
                'localization_rate': result.health.localization_rate,
                'missing_keys_count': result.health.missing_keys_count,
                'dead_keys_count': result.health.dead_keys_count,
                'duplicate_count': result.health.duplicate_count,
            },
            'languages': file_manager.get_language_stats(),
            'hardcoded_strings': [
                {
                    'file': item.file,
                    'line': item.line,
                    'text': item.text,
                    'component': item.component,
                    'category': item.category,
                    'priority': item.priority,
                    'suggested_key': item.suggested_key,
                }
                for item in result.hardcoded_strings
            ],
            'missing_keys': {
                key: {
                    'files': files,
                    'module': file_manager.key_modules.get(key, 'Unknown')
                }
                for key, files in result.missing_keys.items()
            },
            'dead_keys': [
                {
                    'key': key,
                    'module': file_manager.key_modules.get(key, 'Unknown')
                }
                for key in result.dead_keys
            ],
            'duplicates': {
                text: [{
                    'file': item.file,
                    'line': item.line,
                    'component': item.component,
                } for item in items]
                for text, items in result.duplicates.items()
            },
            'component_stats': dict(result.component_stats),
            'file_stats': dict(result.file_stats),
        }

        # Add translation completeness
        missing_translations = file_manager.find_missing_translations()
        untranslated = file_manager.find_untranslated_keys()

        report['translation_status'] = {
            'missing_translations': {
                key: list(langs) for key, langs in missing_translations.items()
            },
            'potentially_untranslated': {
                key: list(langs) for key, langs in untranslated.items()
            },
        }

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(report, f, indent=2, ensure_ascii=False)
            else:
                json.dump(report, f, ensure_ascii=False)

        print(f"\n{Colors.success('✓')} JSON report: {output_path}")

        return output_path

    @staticmethod
    def load(report_path: Path) -> dict:
        """
        Load JSON report from file.

        Args:
            report_path: Path to JSON report

        Returns:
            Report dictionary
        """
        with open(report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
