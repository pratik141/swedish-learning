import { readFile, readdir } from "node:fs/promises";
import { resolveVocabularyPaths } from "./vocabulary-paths.mjs";

const { siteRoot, manifestUrl, chunkDirUrl } = await resolveVocabularyPaths();
const manifest = JSON.parse(await readFile(manifestUrl, "utf8"));
const chunkDir = chunkDirUrl;
const files = (await readdir(chunkDir)).filter((name) => name.endsWith(".json")).sort();

const expected = new Set(manifest.chapters.map((chapter) => `${chapter.slug}.json`));
const ids = new Set();
const keys = new Set();
let total = 0;
const errors = [];

for (const chapter of manifest.chapters) {
  if (!files.includes(`${chapter.slug}.json`)) {
    errors.push(`Missing chunk for ${chapter.label}: ${chapter.slug}.json`);
  }
}

for (const file of files) {
  if (!expected.has(file)) {
    errors.push(`Chunk exists but is not listed in manifest: ${file}`);
  }

  const chunk = JSON.parse(await readFile(new URL(file, chunkDir), "utf8"));
  if (!chunk.chapter?.slug || !Array.isArray(chunk.items)) {
    errors.push(`Invalid chunk shape: ${file}`);
    continue;
  }

  if (chunk.items.length !== chunk.chapter.count) {
    errors.push(`${file}: chapter count ${chunk.chapter.count} does not match ${chunk.items.length} items`);
  }

  for (const item of chunk.items) {
    total += 1;
    for (const field of ["id", "kind", "sv", "en", "hi", "categorySlug", "level", "example"]) {
      if (item[field] === undefined || item[field] === "") {
        errors.push(`${file}: item ${item.id ?? "unknown"} missing ${field}`);
      }
    }

    if (ids.has(item.id)) errors.push(`Duplicate id: ${item.id}`);
    ids.add(item.id);

    const key = `${item.categorySlug}:${item.sv.toLocaleLowerCase("sv-SE")}`;
    if (keys.has(key)) errors.push(`Duplicate Swedish entry in ${item.categorySlug}: ${item.sv}`);
    keys.add(key);

    if (!item.example?.sv || !item.example?.en || !item.example?.hi) {
      errors.push(`${file}: item ${item.id} has incomplete example translations`);
    }
  }
}

if (total !== manifest.meta.total) {
  errors.push(`Manifest total ${manifest.meta.total} does not match ${total} chunk items`);
}

if (manifest.quickIds.length !== manifest.meta.quickTotal) {
  errors.push(`Quick reference count ${manifest.meta.quickTotal} does not match ${manifest.quickIds.length}`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log(`Vocabulary validation passed from ${siteRoot}.`);
console.log(`Chunks: ${files.length}`);
console.log(`Items: ${total}`);
console.log(`Quick reference: ${manifest.quickIds.length}`);
