"""HTML report generator with interactive dashboard."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import html

from ..core.analyzer import AnalysisResult
from ..core.file_manager import LocalizationFileManager
from ..core.health_calculator import HealthCalculator
from ..frameworks.base import BaseAdapter
from ..utils.colors import Colors


class HTMLReporter:
    """
    Interactive HTML dashboard raporu oluşturur.

    Özellikler:
    - Tek sayfa dashboard (tüm veriler embedded)
    - Filtreleme ve arama (JavaScript ile)
    - Collapsible sections
    - Dark/Light mode
    - Export seçenekleri (JSON, CSV)
    """

    @staticmethod
    def generate(
        result: AnalysisResult,
        file_manager: LocalizationFileManager,
        adapter: BaseAdapter,
        output_path: Optional[Path] = None,
        title: str = "Localization Analysis Report"
    ) -> Path:
        """
        Interactive HTML raporu oluşturur.

        Args:
            result: Analiz sonucu
            file_manager: Dosya yöneticisi
            adapter: Framework adapter
            output_path: Çıktı dosya yolu
            title: Rapor başlığı

        Returns:
            Oluşturulan HTML dosyasının yolu
        """
        if output_path is None:
            output_path = Path.cwd() / 'localization_report.html'

        # Rapor verilerini hazırla
        report_data = HTMLReporter._prepare_report_data(result, file_manager, adapter)

        # HTML oluştur
        html_content = HTMLReporter._generate_html(report_data, title)

        # Çıktı dizinini oluştur
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Dosyaya yaz
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"\n{Colors.success('✓')} HTML report: {output_path}")

        return output_path

    @staticmethod
    def _prepare_report_data(
        result: AnalysisResult,
        file_manager: LocalizationFileManager,
        adapter: BaseAdapter
    ) -> dict:
        """Rapor verilerini JSON formatında hazırlar."""
        return {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'framework': adapter.__class__.__name__.replace('Adapter', '').lower(),
            },
            'health': {
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
                    'file': loc.file,
                    'line': loc.line,
                    'component': loc.component,
                } for loc in items]
                for text, items in result.duplicates.items()
            },
            'component_stats': dict(result.component_stats),
            'file_stats': dict(result.file_stats),
            'recommendations': HealthCalculator.get_recommendations(result.health),
        }

    @staticmethod
    def _generate_html(data: dict, title: str) -> str:
        """Tam HTML içeriğini oluşturur."""
        # JSON veriyi JavaScript için hazırla
        # XSS koruması: </script> ve <!-- gibi HTML etiketlerini escape et
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        json_data = json_data.replace('</', '<\\/')  # </script> saldırısını önle
        json_data = json_data.replace('<!--', '<\\!--')  # HTML comment injection önle

        return f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        {HTMLReporter._get_css()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <h1>📊 {html.escape(title)}</h1>
                <div class="header-actions">
                    <button id="themeToggle" class="btn btn-icon" title="Tema değiştir">🌙</button>
                    <button id="exportJSON" class="btn btn-secondary">📥 JSON</button>
                </div>
            </div>
            <p class="meta">
                Framework: <strong id="framework"></strong> |
                Oluşturulma: <strong id="generatedAt"></strong>
            </p>
        </header>

        <!-- Health Score Card -->
        <section class="card health-card">
            <div class="health-score">
                <div class="score-circle" id="scoreCircle">
                    <span class="score-value" id="scoreValue">--</span>
                    <span class="score-grade" id="scoreGrade">-</span>
                </div>
                <div class="score-details">
                    <h2>Sağlık Skoru</h2>
                    <div class="stat-row">
                        <span>Yerelleştirme Oranı:</span>
                        <span id="localizationRate">--%</span>
                    </div>
                </div>
            </div>
            <div class="health-stats">
                <div class="stat-box stat-success">
                    <span class="stat-icon">✅</span>
                    <span class="stat-value" id="localizedCount">0</span>
                    <span class="stat-label">Yerelleştirilmiş</span>
                </div>
                <div class="stat-box stat-warning">
                    <span class="stat-icon">⚠️</span>
                    <span class="stat-value" id="hardcodedCount">0</span>
                    <span class="stat-label">Hardcoded</span>
                </div>
                <div class="stat-box stat-error">
                    <span class="stat-icon">🔴</span>
                    <span class="stat-value" id="missingCount">0</span>
                    <span class="stat-label">Eksik Key</span>
                </div>
                <div class="stat-box stat-info">
                    <span class="stat-icon">🟡</span>
                    <span class="stat-value" id="deadCount">0</span>
                    <span class="stat-label">Kullanılmayan</span>
                </div>
            </div>
        </section>

        <!-- Languages Section -->
        <section class="card collapsible">
            <div class="card-header" onclick="toggleSection(this)">
                <h2>🌍 Diller</h2>
                <span class="collapse-icon">▼</span>
            </div>
            <div class="card-content">
                <table class="data-table" id="languagesTable">
                    <thead>
                        <tr>
                            <th>Dil</th>
                            <th>Key Sayısı</th>
                            <th>Eksik</th>
                            <th>Tamamlanma</th>
                        </tr>
                    </thead>
                    <tbody id="languagesBody"></tbody>
                </table>
            </div>
        </section>

        <!-- Hardcoded Strings Section -->
        <section class="card collapsible">
            <div class="card-header" onclick="toggleSection(this)">
                <h2>⚠️ Hardcoded Stringler</h2>
                <span class="badge" id="hardcodedBadge">0</span>
                <span class="collapse-icon">▼</span>
            </div>
            <div class="card-content">
                <div class="filter-bar">
                    <input type="text" id="hardcodedSearch" placeholder="Ara..." class="search-input">
                    <select id="hardcodedPriority" class="filter-select">
                        <option value="">Tüm Öncelikler</option>
                        <option value="9">P9 - Kritik</option>
                        <option value="8">P8+</option>
                        <option value="7">P7+</option>
                    </select>
                </div>
                <div class="table-container">
                    <table class="data-table" id="hardcodedTable">
                        <thead>
                            <tr>
                                <th>P</th>
                                <th>Dosya</th>
                                <th>Satır</th>
                                <th>Text</th>
                                <th>Önerilen Key</th>
                            </tr>
                        </thead>
                        <tbody id="hardcodedBody"></tbody>
                    </table>
                </div>
                <div class="pagination" id="hardcodedPagination"></div>
            </div>
        </section>

        <!-- Missing Keys Section -->
        <section class="card collapsible">
            <div class="card-header" onclick="toggleSection(this)">
                <h2>🔴 Eksik Key'ler</h2>
                <span class="badge" id="missingBadge">0</span>
                <span class="collapse-icon">▼</span>
            </div>
            <div class="card-content">
                <div class="filter-bar">
                    <input type="text" id="missingSearch" placeholder="Ara..." class="search-input">
                </div>
                <div class="table-container">
                    <table class="data-table" id="missingTable">
                        <thead>
                            <tr>
                                <th>Key</th>
                                <th>Modül</th>
                                <th>Kullanıldığı Dosyalar</th>
                            </tr>
                        </thead>
                        <tbody id="missingBody"></tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- Dead Keys Section -->
        <section class="card collapsible collapsed">
            <div class="card-header" onclick="toggleSection(this)">
                <h2>🟡 Kullanılmayan Key'ler</h2>
                <span class="badge" id="deadBadge">0</span>
                <span class="collapse-icon">▼</span>
            </div>
            <div class="card-content">
                <div class="filter-bar">
                    <input type="text" id="deadSearch" placeholder="Ara..." class="search-input">
                </div>
                <div class="table-container">
                    <table class="data-table" id="deadTable">
                        <thead>
                            <tr>
                                <th>Key</th>
                                <th>Modül</th>
                            </tr>
                        </thead>
                        <tbody id="deadBody"></tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- Duplicates Section -->
        <section class="card collapsible collapsed">
            <div class="card-header" onclick="toggleSection(this)">
                <h2>📦 Tekrarlayan Stringler</h2>
                <span class="badge" id="duplicatesBadge">0</span>
                <span class="collapse-icon">▼</span>
            </div>
            <div class="card-content">
                <div class="table-container">
                    <table class="data-table" id="duplicatesTable">
                        <thead>
                            <tr>
                                <th>Text</th>
                                <th>Kullanım</th>
                                <th>Lokasyonlar</th>
                            </tr>
                        </thead>
                        <tbody id="duplicatesBody"></tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- Recommendations Section -->
        <section class="card">
            <div class="card-header">
                <h2>💡 Öneriler</h2>
            </div>
            <div class="card-content">
                <ul class="recommendations-list" id="recommendationsList"></ul>
            </div>
        </section>

        <footer>
            <p>Localization Analyzer tarafından oluşturuldu</p>
        </footer>
    </div>

    <script>
        // Rapor verileri
        const reportData = {json_data};

        {HTMLReporter._get_javascript()}
    </script>
</body>
</html>'''

    @staticmethod
    def _get_css() -> str:
        """CSS stillerini döndürür."""
        return '''
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-card: #ffffff;
            --text-primary: #212529;
            --text-secondary: #6c757d;
            --border-color: #dee2e6;
            --success: #28a745;
            --warning: #ffc107;
            --error: #dc3545;
            --info: #17a2b8;
            --primary: #007bff;
            --shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        [data-theme="dark"] {
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-card: #0f3460;
            --text-primary: #e4e4e4;
            --text-secondary: #adb5bd;
            --border-color: #4a4a6a;
            --shadow: 0 2px 8px rgba(0,0,0,0.3);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            transition: background 0.3s, color 0.3s;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }

        header {
            margin-bottom: 32px;
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }

        header h1 {
            font-size: 28px;
            font-weight: 700;
        }

        .header-actions {
            display: flex;
            gap: 8px;
        }

        .meta {
            color: var(--text-secondary);
            margin-top: 8px;
        }

        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }

        .btn-icon {
            background: var(--bg-secondary);
            font-size: 18px;
            padding: 8px 12px;
        }

        .btn-secondary {
            background: var(--bg-secondary);
            color: var(--text-primary);
        }

        .btn:hover {
            opacity: 0.8;
            transform: translateY(-1px);
        }

        .card {
            background: var(--bg-card);
            border-radius: 12px;
            box-shadow: var(--shadow);
            margin-bottom: 24px;
            overflow: hidden;
        }

        .card-header {
            padding: 16px 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            user-select: none;
        }

        .card-header h2 {
            font-size: 18px;
            flex-grow: 1;
        }

        .collapse-icon {
            transition: transform 0.3s;
        }

        .collapsed .collapse-icon {
            transform: rotate(-90deg);
        }

        .collapsed .card-content {
            display: none;
        }

        .card-content {
            padding: 24px;
        }

        .badge {
            background: var(--primary);
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }

        /* Health Card */
        .health-card {
            background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-secondary) 100%);
        }

        .health-card .card-content {
            padding: 0;
        }

        .health-score {
            display: flex;
            align-items: center;
            gap: 32px;
            padding: 32px;
        }

        .score-circle {
            width: 140px;
            height: 140px;
            border-radius: 50%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: conic-gradient(var(--success) 0deg, var(--bg-secondary) 0deg);
            position: relative;
        }

        .score-circle::before {
            content: '';
            position: absolute;
            width: 110px;
            height: 110px;
            background: var(--bg-card);
            border-radius: 50%;
        }

        .score-value, .score-grade {
            position: relative;
            z-index: 1;
        }

        .score-value {
            font-size: 36px;
            font-weight: 700;
        }

        .score-grade {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-secondary);
        }

        .score-details h2 {
            font-size: 24px;
            margin-bottom: 8px;
        }

        .stat-row {
            display: flex;
            justify-content: space-between;
            gap: 16px;
            color: var(--text-secondary);
        }

        .health-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            padding: 0 32px 32px;
        }

        .stat-box {
            background: var(--bg-secondary);
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }

        .stat-icon {
            font-size: 24px;
            display: block;
            margin-bottom: 8px;
        }

        .stat-value {
            font-size: 28px;
            font-weight: 700;
            display: block;
        }

        .stat-label {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .stat-success .stat-value { color: var(--success); }
        .stat-warning .stat-value { color: var(--warning); }
        .stat-error .stat-value { color: var(--error); }
        .stat-info .stat-value { color: var(--info); }

        /* Filter Bar */
        .filter-bar {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
        }

        .search-input {
            flex: 1;
            padding: 10px 16px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            font-size: 14px;
            background: var(--bg-secondary);
            color: var(--text-primary);
        }

        .filter-select {
            padding: 10px 16px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            font-size: 14px;
            background: var(--bg-secondary);
            color: var(--text-primary);
        }

        /* Tables */
        .table-container {
            overflow-x: auto;
        }

        .data-table {
            width: 100%;
            border-collapse: collapse;
        }

        .data-table th,
        .data-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }

        .data-table th {
            background: var(--bg-secondary);
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            color: var(--text-secondary);
        }

        .data-table tr:hover {
            background: var(--bg-secondary);
        }

        .data-table .priority-9 { color: var(--error); font-weight: 700; }
        .data-table .priority-8 { color: var(--warning); font-weight: 600; }
        .data-table .priority-7 { color: var(--info); }

        .text-cell {
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .file-cell {
            font-family: monospace;
            font-size: 12px;
        }

        .key-cell {
            font-family: monospace;
            font-size: 13px;
            color: var(--primary);
        }

        /* Progress Bar */
        .progress-bar {
            height: 8px;
            background: var(--bg-secondary);
            border-radius: 4px;
            overflow: hidden;
            min-width: 100px;
        }

        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }

        .progress-fill.high { background: var(--success); }
        .progress-fill.medium { background: var(--warning); }
        .progress-fill.low { background: var(--error); }

        /* Pagination */
        .pagination {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-top: 16px;
        }

        .pagination button {
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            background: var(--bg-secondary);
            color: var(--text-primary);
            border-radius: 4px;
            cursor: pointer;
        }

        .pagination button.active {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }

        .pagination button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* Recommendations */
        .recommendations-list {
            list-style: none;
        }

        .recommendations-list li {
            padding: 12px 16px;
            margin-bottom: 8px;
            background: var(--bg-secondary);
            border-radius: 8px;
            border-left: 4px solid var(--primary);
        }

        /* Footer */
        footer {
            text-align: center;
            padding: 24px;
            color: var(--text-secondary);
            font-size: 14px;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .health-score {
                flex-direction: column;
                text-align: center;
            }

            .health-stats {
                grid-template-columns: repeat(2, 1fr);
            }

            .filter-bar {
                flex-direction: column;
            }

            .header-content {
                flex-direction: column;
                align-items: flex-start;
            }
        }
        '''

    @staticmethod
    def _get_javascript() -> str:
        """JavaScript kodunu döndürür."""
        return '''
        // Sayfa yüklendiğinde başlat
        document.addEventListener('DOMContentLoaded', function() {
            initDashboard();
            initTheme();
            initFilters();
            initExport();
        });

        function initDashboard() {
            // Metadata
            document.getElementById('framework').textContent = reportData.metadata.framework;
            document.getElementById('generatedAt').textContent =
                new Date(reportData.metadata.generated_at).toLocaleString('tr-TR');

            // Health Score
            const health = reportData.health;
            document.getElementById('scoreValue').textContent = health.score;
            document.getElementById('scoreGrade').textContent = health.grade;
            document.getElementById('localizationRate').textContent = health.localization_rate.toFixed(1) + '%';
            document.getElementById('localizedCount').textContent = health.localized_count.toLocaleString();
            document.getElementById('hardcodedCount').textContent = health.hardcoded_count.toLocaleString();
            document.getElementById('missingCount').textContent = health.missing_keys_count;
            document.getElementById('deadCount').textContent = health.dead_keys_count;

            // Score circle gradient
            const scoreCircle = document.getElementById('scoreCircle');
            const degree = (health.score / 100) * 360;
            let color = health.score >= 80 ? '#28a745' : health.score >= 60 ? '#ffc107' : '#dc3545';
            scoreCircle.style.background = `conic-gradient(${color} ${degree}deg, var(--bg-secondary) ${degree}deg)`;

            // Badges
            document.getElementById('hardcodedBadge').textContent = reportData.hardcoded_strings.length;
            document.getElementById('missingBadge').textContent = Object.keys(reportData.missing_keys).length;
            document.getElementById('deadBadge').textContent = reportData.dead_keys.length;
            document.getElementById('duplicatesBadge').textContent = Object.keys(reportData.duplicates).length;

            // Tables
            renderLanguages();
            renderHardcoded();
            renderMissing();
            renderDead();
            renderDuplicates();
            renderRecommendations();
        }

        // Languages Table
        function renderLanguages() {
            const tbody = document.getElementById('languagesBody');
            const langs = reportData.languages;

            tbody.innerHTML = Object.entries(langs).map(([code, stats]) => {
                const percent = stats.completion_percent;
                const barClass = percent >= 90 ? 'high' : percent >= 70 ? 'medium' : 'low';
                return `
                    <tr>
                        <td><strong>${code}</strong></td>
                        <td>${stats.total_keys}</td>
                        <td>${stats.missing_keys || 0}</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill ${barClass}" style="width: ${percent}%"></div>
                            </div>
                            <span>${percent.toFixed(1)}%</span>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        // Hardcoded Strings - Paginated
        let hardcodedPage = 1;
        const hardcodedPerPage = 20;

        function renderHardcoded(filter = '', priority = '') {
            const tbody = document.getElementById('hardcodedBody');
            let data = reportData.hardcoded_strings;

            // Filter
            if (filter) {
                const lowerFilter = filter.toLowerCase();
                data = data.filter(item =>
                    item.text.toLowerCase().includes(lowerFilter) ||
                    item.file.toLowerCase().includes(lowerFilter)
                );
            }

            if (priority) {
                const minPriority = parseInt(priority);
                data = data.filter(item => item.priority >= minPriority);
            }

            // Pagination
            const total = data.length;
            const pages = Math.ceil(total / hardcodedPerPage);
            const start = (hardcodedPage - 1) * hardcodedPerPage;
            const pageData = data.slice(start, start + hardcodedPerPage);

            tbody.innerHTML = pageData.map(item => {
                const priorityClass = item.priority >= 9 ? 'priority-9' :
                                     item.priority >= 8 ? 'priority-8' :
                                     item.priority >= 7 ? 'priority-7' : '';
                return `
                    <tr>
                        <td class="${priorityClass}">P${item.priority}</td>
                        <td class="file-cell">${escapeHtml(item.file)}</td>
                        <td>${item.line}</td>
                        <td class="text-cell" title="${escapeHtml(item.text)}">${escapeHtml(item.text.substring(0, 50))}${item.text.length > 50 ? '...' : ''}</td>
                        <td class="key-cell">${escapeHtml(item.suggested_key)}</td>
                    </tr>
                `;
            }).join('');

            // Pagination controls
            renderPagination('hardcodedPagination', pages, hardcodedPage, (page) => {
                hardcodedPage = page;
                renderHardcoded(filter, priority);
            });
        }

        // Missing Keys
        function renderMissing(filter = '') {
            const tbody = document.getElementById('missingBody');
            let entries = Object.entries(reportData.missing_keys);

            if (filter) {
                const lowerFilter = filter.toLowerCase();
                entries = entries.filter(([key]) => key.toLowerCase().includes(lowerFilter));
            }

            tbody.innerHTML = entries.map(([key, data]) => `
                <tr>
                    <td class="key-cell">${escapeHtml(key)}</td>
                    <td>${escapeHtml(data.module)}</td>
                    <td class="file-cell">${data.files.slice(0, 3).map(f => escapeHtml(f)).join(', ')}${data.files.length > 3 ? ` +${data.files.length - 3} more` : ''}</td>
                </tr>
            `).join('');
        }

        // Dead Keys
        function renderDead(filter = '') {
            const tbody = document.getElementById('deadBody');
            let data = reportData.dead_keys;

            if (filter) {
                const lowerFilter = filter.toLowerCase();
                data = data.filter(item => item.key.toLowerCase().includes(lowerFilter));
            }

            tbody.innerHTML = data.map(item => `
                <tr>
                    <td class="key-cell">${escapeHtml(item.key)}</td>
                    <td>${escapeHtml(item.module)}</td>
                </tr>
            `).join('');
        }

        // Duplicates
        function renderDuplicates() {
            const tbody = document.getElementById('duplicatesBody');
            const entries = Object.entries(reportData.duplicates);

            tbody.innerHTML = entries.map(([text, locations]) => `
                <tr>
                    <td class="text-cell" title="${escapeHtml(text)}">${escapeHtml(text.substring(0, 40))}${text.length > 40 ? '...' : ''}</td>
                    <td>${locations.length}</td>
                    <td class="file-cell">${locations.slice(0, 2).map(l => `${escapeHtml(l.file)}:${l.line}`).join(', ')}${locations.length > 2 ? ` +${locations.length - 2}` : ''}</td>
                </tr>
            `).join('');
        }

        // Recommendations
        function renderRecommendations() {
            const list = document.getElementById('recommendationsList');
            list.innerHTML = reportData.recommendations.map(rec =>
                `<li>${escapeHtml(rec)}</li>`
            ).join('');
        }

        // Pagination Helper
        function renderPagination(containerId, totalPages, currentPage, onChange) {
            const container = document.getElementById(containerId);
            if (totalPages <= 1) {
                container.innerHTML = '';
                return;
            }

            let html = `<button ${currentPage === 1 ? 'disabled' : ''} onclick="arguments[0].stopPropagation()">◀</button>`;

            for (let i = 1; i <= Math.min(totalPages, 5); i++) {
                html += `<button class="${i === currentPage ? 'active' : ''}">${i}</button>`;
            }

            if (totalPages > 5) {
                html += `<span>...</span><button>${totalPages}</button>`;
            }

            html += `<button ${currentPage === totalPages ? 'disabled' : ''}>▶</button>`;

            container.innerHTML = html;

            // Add click handlers
            container.querySelectorAll('button').forEach((btn, idx) => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    let newPage = currentPage;
                    if (idx === 0) newPage = Math.max(1, currentPage - 1);
                    else if (idx === container.querySelectorAll('button').length - 1) newPage = Math.min(totalPages, currentPage + 1);
                    else newPage = parseInt(btn.textContent);
                    if (newPage !== currentPage) onChange(newPage);
                });
            });
        }

        // Section Toggle
        function toggleSection(header) {
            header.parentElement.classList.toggle('collapsed');
        }

        // Theme Toggle
        function initTheme() {
            const saved = localStorage.getItem('theme') || 'light';
            document.documentElement.setAttribute('data-theme', saved);
            updateThemeButton(saved);

            document.getElementById('themeToggle').addEventListener('click', () => {
                const current = document.documentElement.getAttribute('data-theme');
                const next = current === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', next);
                localStorage.setItem('theme', next);
                updateThemeButton(next);
            });
        }

        function updateThemeButton(theme) {
            document.getElementById('themeToggle').textContent = theme === 'dark' ? '☀️' : '🌙';
        }

        // Filters
        function initFilters() {
            document.getElementById('hardcodedSearch').addEventListener('input', (e) => {
                hardcodedPage = 1;
                renderHardcoded(e.target.value, document.getElementById('hardcodedPriority').value);
            });

            document.getElementById('hardcodedPriority').addEventListener('change', (e) => {
                hardcodedPage = 1;
                renderHardcoded(document.getElementById('hardcodedSearch').value, e.target.value);
            });

            document.getElementById('missingSearch').addEventListener('input', (e) => {
                renderMissing(e.target.value);
            });

            document.getElementById('deadSearch').addEventListener('input', (e) => {
                renderDead(e.target.value);
            });
        }

        // Export
        function initExport() {
            document.getElementById('exportJSON').addEventListener('click', () => {
                const dataStr = JSON.stringify(reportData, null, 2);
                const blob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'localization_report.json';
                a.click();
                URL.revokeObjectURL(url);
            });
        }

        // Utility
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        '''
