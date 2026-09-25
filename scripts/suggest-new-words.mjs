import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const distRoot = new URL("../dist/", import.meta.url);
const outDir = new URL("../reports/", import.meta.url);
const chunkDir = new URL("data/chunks/", distRoot);

const candidateBank = [
  ["A1", "Fruits", "en clementin", "clementine", "क्लेमेंटाइन"],
  ["A1", "Food & drinks", "havregryn", "oats", "ओट्स"],
  ["A1", "Food & drinks", "jordnötssmör", "peanut butter", "पीनट बटर"],
  ["A2", "Health & body", "en vårdcentral", "health centre", "स्वास्थ्य केंद्र"],
  ["A2", "Health & body", "ett apotekskvitto", "pharmacy receipt", "फार्मेसी रसीद"],
  ["A2", "Transport & travel", "en försening", "delay", "देरी"],
  ["A2", "Transport & travel", "en ersättningsbuss", "replacement bus", "बदली बस"],
  ["A2", "Shopping", "ett öppet köp", "return period", "रिटर्न अवधि"],
  ["A2", "Shopping", "en reklamation", "complaint / claim", "शिकायत"],
  ["A2", "Work & office", "en provanställning", "probationary employment", "प्रोबेशन नौकरी"],
  ["A2", "Work & office", "en tillsvidareanställning", "permanent employment", "स्थायी नौकरी"],
  ["B1", "Public services & documents", "Skatteverket", "Swedish Tax Agency", "स्वीडिश टैक्स एजेंसी"],
  ["B1", "Public services & documents", "Försäkringskassan", "Social Insurance Agency", "सोशल इंश्योरेंस एजेंसी"],
  ["B1", "Housing & repairs", "en felanmälan", "fault report", "खराबी रिपोर्ट"],
  ["B1", "Housing & repairs", "en bostadskö", "housing queue", "हाउसिंग क्यू"],
  ["A2", "Phone & digital life", "tvåfaktorsinloggning", "two-factor login", "टू-फैक्टर लॉगिन"],
  ["A2", "Emergency & safety", "ett nödnummer", "emergency number", "आपात नंबर"],
  ["A1", "Feelings & small talk", "förkyld", "having a cold", "ज़ुकाम होना"],
];

const files = (await readdir(chunkDir)).filter((name) => name.endsWith(".json"));
const existing = new Set();

for (const file of files) {
  const chunk = JSON.parse(await readFile(new URL(file, chunkDir), "utf8"));
  for (const item of chunk.items) existing.add(item.sv.toLocaleLowerCase("sv-SE"));
}

const suggestions = candidateBank.filter(([, , swedish]) => !existing.has(swedish.toLocaleLowerCase("sv-SE")));

await mkdir(outDir, { recursive: true });
const body = [
  "# Vocabulary suggestions",
  "",
  "These are candidate everyday Swedish words that are not currently present in the vocabulary chunks.",
  "Review the Swedish, English, Hindi, forms, pronunciation, and examples before adding them.",
  "",
  "| Level | Component | Swedish | English | Hindi |",
  "| --- | --- | --- | --- | --- |",
  ...suggestions.map(([level, component, swedish, english, hindi]) => `| ${level} | ${component} | ${swedish} | ${english} | ${hindi} |`),
  "",
].join("\n");

const outPath = new URL("vocabulary_suggestions.md", outDir);
await writeFile(outPath, body, "utf8");
console.log(`Wrote ${suggestions.length} suggestions to ${fileURLToPath(outPath)}`);
