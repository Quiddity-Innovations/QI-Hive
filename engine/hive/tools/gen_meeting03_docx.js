const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType } = require('docx');
const fs = require('fs');

const border = { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text, bold: true })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text })] });
}
function p(text) {
  return new Paragraph({ children: [new TextRun(text || '')] });
}
function bullet(text) {
  return new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [new TextRun(text)] });
}
function makeTable(headers, rows, colWidths) {
  const total = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => new TableCell({
          borders, margins: cellMargins,
          width: { size: colWidths[i], type: WidthType.DXA },
          shading: { fill: '2E75B6', type: ShadingType.CLEAR },
          children: [new Paragraph({ children: [new TextRun({ text: h, bold: true, color: 'FFFFFF' })] })]
        }))
      }),
      ...rows.map(row => new TableRow({
        children: row.map((cell, i) => new TableCell({
          borders, margins: cellMargins,
          width: { size: colWidths[i], type: WidthType.DXA },
          children: [new Paragraph({ children: [new TextRun(cell)] })]
        }))
      }))
    ]
  });
}

const doc = new Document({
  numbering: {
    config: [{
      reference: 'bullets',
      levels: [{ level: 0, format: 'bullet', text: '\u2022', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }]
    }]
  },
  styles: {
    default: { document: { run: { font: 'Arial', size: 24 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 36, bold: true, font: 'Arial', color: '2E75B6' },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: 'Arial', color: '404040' },
        paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
    },
    children: [
      h1('Claude Meeting 03 \u2014 Build Phase 2'),
      h2('Date: 2026-04-07 | Project: QI Claude Manager'),
      p(''),
      h1('\u2705 Completed This Session'),
      p('The following items were built, fixed, or decided:'),
      p(''),
      makeTable(['Item', 'Status'], [
        ['Install SQLite MCP (mcp-server-sqlite)', '\u2705 Done \u2014 sqlite-maia + sqlite-naya registered'],
        ['Install Git MCP (@cyanheads/git-mcp-server v2.10.5)', '\u2705 Done \u2014 registered in .claude.json'],
        ['Fix Naya root 404', '\u2705 Code patched \u2014 GET / added \u2014 needs admin service restart'],
        ['/api/ping endpoint on Dashboard', '\u2705 Live \u2014 Architect\u2192Builder\u2192Inspector chain PROVEN'],
        ['/api/scout/digest endpoint on Dashboard', '\u2705 Live \u2014 proxies NEXUS, returns top 5 AI headlines'],
        ['fetch-ai-news skill created', '\u2705 C:\\Claude\\Skills\\fetch-ai-news\\skill.md'],
        ['Starlette downgrade fix', '\u2705 Pinned to 0.41.3 after mcp-server-sqlite broke FastAPI'],
        ['status.json + LATEST.md updated', '\u2705 Done'],
        ['Claude Manager committed to git', '\u2705 Done (no GitHub remote yet)'],
      ], [5200, 4160]),
      p(''),
      h1('\uD83C\uDFC6 Milestone: Agent Chain End-to-End PROVEN'),
      p('The full Architect \u2192 Builder \u2192 Inspector chain ran on a real task (/api/ping) with zero human code involvement:'),
      bullet('Architect: Read server.py, produced exact spec (file, line number, function signature, test assertions)'),
      bullet('Builder: Implemented exactly to spec in 6 tool calls'),
      bullet('Inspector: Code review PASS + live assertion test PASS (all 4 assertions)'),
      p(''),
      h1('\uD83D\uDD04 Next Up (Meeting 04)'),
      makeTable(['#', 'Task'], [
        ['1', 'OpenSpace skill evolution test \u2014 search_skills on fetch-ai-news, session-summary, git-commit'],
        ['2', 'Restart NayaBot service (admin) to activate root 404 fix'],
        ['3', 'Start ClaudeManager NSSM service (admin: sc continue ClaudeManager)'],
        ['4', 'Add GitHub remote + push C:\\Claude to Quiddity-Innovations org'],
        ['5', 'Add /api/ping test to test_dashboard_api.py'],
        ['6', 'Wire sqlite-maia MCP \u2014 query maia.db directly from Claude'],
        ['7', 'Git MCP first real use \u2014 git_log + git_status on live repos'],
      ], [800, 8560]),
      p(''),
      h1('\uD83D\uDE80 In Development'),
      bullet('Agent workflow system \u2014 7 agents \u2014 chain proven, team coordination next'),
      bullet('Dashboard v2 \u2014 5 pages + 7 API endpoints \u2014 expanding to scout/DB views'),
      bullet('OpenSpace skill evolution \u2014 MCPs registered, test deferred to Meeting 04'),
      bullet('Naya root fix \u2014 code done, waiting on admin restart'),
      p(''),
      h1('\uD83C\uDF05 Future Enhancements'),
      bullet('Wire all 4 QI databases via SQLite MCP (Maia, Naya, NEXUS, FileHQ)'),
      bullet('Agent memory via sqlite-maia \u2014 agents query/write to DB'),
      bullet('Real claude-peers messaging test between two agents'),
      bullet('ClaudeManager GitHub repo under Quiddity-Innovations org'),
      p(''),
      h1('\u26A0\uFE0F Known Issues Requiring Admin'),
      makeTable(['Issue', 'Fix'], [
        ['ClaudeManager NSSM service PAUSED', 'Run: sc continue ClaudeManager (admin terminal)'],
        ['NayaBot root 404 active in code but not live', 'naya_control.bat option 3 (Restart) as admin'],
        ['Starlette pinned to 0.41.3', 'May conflict with mcp-server-sqlite as live MCP server \u2014 monitor'],
      ], [4680, 4680]),
      p(''),
      h1('\uD83D\uDCC1 Documents Updated'),
      makeTable(['File', 'Action'], [
        ['C:\\NAYA\\naya_server.py', 'UPDATED \u2014 added GET / root route'],
        ['C:\\Claude\\Dashboard\\server.py', 'UPDATED \u2014 /api/ping + /api/scout/digest + timezone import'],
        ['C:\\Claude\\Skills\\fetch-ai-news\\skill.md', 'CREATED'],
        ['C:\\Claude\\Tools\\patch_mcp_config.py', 'CREATED'],
        ['C:\\Claude\\Tools\\gen_meeting03_docx.js', 'CREATED'],
        ['C:\\Users\\renne\\.claude.json', 'UPDATED \u2014 3 new MCPs registered'],
        ['C:\\Claude\\status.json', 'UPDATED'],
        ['C:\\Claude\\Session Summaries\\LATEST.md', 'UPDATED'],
        ['C:\\Claude\\Session Summaries\\Claude_Meeting_03_2026-04-07.docx', 'CREATED (this file)'],
      ], [5200, 4160]),
      p(''),
      h1('\uD83D\uDE80 How to Start Meeting 04'),
      p('Open new Claude Code session. Name it: Claude Meeting 04 \u2014 OpenSpace Test + Commits + DB Queries'),
      p(''),
      p('Say: "Start Meeting 04. Read LATEST.md at C:\\Claude\\Session Summaries\\LATEST.md and status.json at C:\\Claude\\status.json. Then begin the agenda."'),
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  const out = 'C:/Claude/Session Summaries/Claude_Meeting_03_2026-04-07.docx';
  fs.writeFileSync(out, buf);
  console.log('Saved:', out);
}).catch(err => { console.error('Error:', err.message); process.exit(1); });
