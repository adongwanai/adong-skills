#!/usr/bin/env node
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

if (!process.argv[2]) throw new Error("usage: build_tracker.mjs <workspace>");
const workspace = await fs.realpath(path.resolve(process.argv[2]));
const skillDir = await fs.realpath(path.resolve(path.dirname(fileURLToPath(import.meta.url)), ".."));
const nestedRepository = path.resolve(skillDir, "../..");
const repository = path.basename(path.dirname(skillDir)) === "skills"
  && existsSync(path.join(nestedRepository, "examples", "anonymous-candidate"))
  ? nestedRepository
  : path.dirname(skillDir);
const publicExamples = new Set([
  path.join(repository, "examples", "adong-public-case"),
  path.join(repository, "examples", "anonymous-candidate"),
]);
if ((workspace === repository || workspace.startsWith(`${repository}${path.sep}`)) && !publicExamples.has(workspace)) {
  throw new Error("candidate workspace must be outside the Agent Career Kit repository");
}

const moduleSpecifier = process.env.CODEX_ARTIFACT_TOOL_PATH
  ? pathToFileURL(process.env.CODEX_ARTIFACT_TOOL_PATH).href
  : "@oai/artifact-tool";
const { SpreadsheetFile, Workbook } = await import(moduleSpecifier);

const applicationDir = path.join(workspace, "outputs", "application");
const previewDir = path.join(applicationDir, "qa");
await fs.mkdir(previewDir, { recursive: true });

const applicationsCsv = await fs.readFile(path.join(applicationDir, "application-tracker.csv"), "utf8");
const interviewsCsv = await fs.readFile(path.join(applicationDir, "interview-schedule.csv"), "utf8");
const offersCsv = await fs.readFile(path.join(applicationDir, "offer-comparison.csv"), "utf8");

const rowCount = (csv) => Math.max(1, csv.trimEnd().split(/\r?\n/).length);
const lastRow = (csv) => rowCount(csv);
const workbook = await Workbook.fromCSV(applicationsCsv, { sheetName: "Applications" });
await workbook.fromCSV(interviewsCsv, { sheetName: "Interviews" });
await workbook.fromCSV(offersCsv, { sheetName: "Offers" });
const summary = workbook.worksheets.add("Summary");

const accent = "#B42318";
const dark = "#161616";
const line = "#D9D9D4";
const pale = "#F7F7F5";

function styleDataSheet(sheet, range, widths, rows) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  const used = sheet.getRange(range);
  used.format = { font: { name: "Aptos", size: 10, color: dark }, verticalAlignment: "center", wrapText: true };
  used.getRow(0).format = {
    fill: dark,
    font: { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" },
    rowHeight: 28,
    verticalAlignment: "center",
  };
  used.format.borders = {
    insideHorizontal: { style: "thin", color: line },
    bottom: { style: "thin", color: line },
  };
  widths.forEach((width, index) => {
    sheet.getRangeByIndexes(0, index, rows, 1).format.columnWidth = width;
  });
}

const applications = workbook.worksheets.getItem("Applications");
const interviews = workbook.worksheets.getItem("Interviews");
const offers = workbook.worksheets.getItem("Offers");
const appRows = Math.max(2, lastRow(applicationsCsv));
const interviewRows = Math.max(2, lastRow(interviewsCsv));
const offerRows = Math.max(2, lastRow(offersCsv));

styleDataSheet(applications, `A1:I${appRows}`, [15, 22, 25, 20, 14, 16, 14, 26, 28], appRows);
styleDataSheet(interviews, `A1:H${interviewRows}`, [15, 22, 25, 17, 14, 24, 16, 32], interviewRows);
styleDataSheet(offers, `A1:K${offerRows}`, [15, 22, 24, 14, 16, 16, 14, 24, 24, 14, 30], offerRows);
applications.tables.add(`A1:I${appRows}`, true, "ApplicationsTable");
interviews.tables.add(`A1:H${interviewRows}`, true, "InterviewsTable");
offers.tables.add(`A1:K${offerRows}`, true, "OffersTable");

applications.getRange("F2:F25").dataValidation = {
  rule: { type: "list", values: ["researching", "ready", "referred", "applied", "screen", "interviewing", "offer", "rejected", "paused", "withdrawn"] },
};
applications.getRange("F2:F25").conditionalFormats.add("containsText", {
  text: "offer",
  format: { fill: "#DDF3E4", font: { color: "#176B36", bold: true } },
});
applications.getRange("F2:F25").conditionalFormats.add("containsText", {
  text: "rejected",
  format: { fill: "#FCE4E1", font: { color: accent } },
});
if (appRows > 1) applications.getRange(`G2:G${appRows}`).format.numberFormat = "yyyy-mm-dd";
if (interviewRows > 1) interviews.getRange(`E2:E${interviewRows}`).format.numberFormat = "yyyy-mm-dd";
if (offerRows > 1) offers.getRange(`J2:J${offerRows}`).format.numberFormat = "yyyy-mm-dd";

summary.showGridLines = false;
summary.getRange("A1:F1").merge();
summary.getRange("A1").values = [["Agent Career Pipeline"]];
summary.getRange("A1:F1").format = {
  fill: dark,
  font: { name: "Aptos Display", size: 20, bold: true, color: "#FFFFFF" },
  rowHeight: 44,
  verticalAlignment: "center",
};
summary.getRange("A3:B3").values = [["Pipeline", "Current"]];
summary.getRange("A4:A7").values = [["Applications"], ["Interviewing"], ["Offers"], ["Next actions missing"]];
summary.getRange("B4").formulas = [["=COUNTA('Applications'!$A$2:$A$200)"]];
summary.getRange("B5").formulas = [["=COUNTIF('Applications'!$F$2:$F$200,\"interviewing\")"]];
summary.getRange("B6").formulas = [["=COUNTIF('Applications'!$F$2:$F$200,\"offer\")"]];
summary.getRange("B7").formulas = [["=COUNTBLANK('Applications'!$H$2:$H$200)-COUNTBLANK('Applications'!$A$2:$A$200)"]];
summary.getRange("A3:B3").format = { fill: accent, font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A4:B7").format = {
  fill: pale,
  font: { name: "Aptos", size: 11, color: dark },
  borders: { insideHorizontal: { style: "thin", color: line }, bottom: { style: "thin", color: line } },
  rowHeight: 26,
};
summary.getRange("B4:B7").format = { font: { size: 14, bold: true, color: accent }, numberFormat: "0" };
summary.getRange("A9:F9").merge();
summary.getRange("A9").values = [["CSV files are canonical; this workbook is an operational view."]];
summary.getRange("A9:F9").format = { font: { italic: true, color: "#5F6468" }, rowHeight: 26 };
summary.getRange("A1:F12").format.columnWidth = 16;
summary.getRange("A:A").format.columnWidth = 24;
summary.getRange("B:B").format.columnWidth = 16;

const formulaScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula scan",
});
console.log(formulaScan.ndjson);

const previewRanges = {
  Summary: "A1:F9",
  Applications: `A1:I${Math.max(6, appRows)}`,
  Interviews: `A1:H${Math.max(6, interviewRows)}`,
  Offers: `A1:K${Math.max(6, offerRows)}`,
};
for (const [sheetName, range] of Object.entries(previewRanges)) {
  const preview = await workbook.render({ sheetName, range, scale: 1.5, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
const outputPath = path.join(applicationDir, "career-tracker.xlsx");
await output.save(outputPath);
await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });
console.log(outputPath);
