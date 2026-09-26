import { access } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = process.cwd();

async function exists(candidate) {
  try {
    await access(candidate);
    return true;
  } catch {
    return false;
  }
}

export async function resolveVocabularyPaths() {
  const envDist = process.env.VOCAB_DIST_DIR ? path.resolve(repoRoot, process.env.VOCAB_DIST_DIR) : null;
  const candidates = [
    envDist,
    path.resolve(repoRoot, "docs"),
    path.resolve(scriptDir, "../dist"),
    path.resolve(repoRoot, "dist"),
    path.resolve(repoRoot, "swedish-vocab-site/dist"),
  ].filter(Boolean);

  for (const distRoot of candidates) {
    const manifestPath = path.join(distRoot, "data/manifest.json");
    const chunkDir = path.join(distRoot, "data/chunks");
    if (await exists(manifestPath) && await exists(chunkDir)) {
      const siteRoot = path.dirname(distRoot);
      return {
        siteRoot,
        distRoot,
        manifestUrl: pathToFileURL(manifestPath),
        chunkDirUrl: pathToFileURL(`${chunkDir}${path.sep}`),
        reportDir: path.join(siteRoot, "reports"),
      };
    }
  }

  throw new Error(
    [
      "Could not find vocabulary data.",
      "Expected one of:",
      ...candidates.map((candidate) => `- ${path.join(candidate, "data/manifest.json")}`),
      "",
      "If your site is in another folder, set VOCAB_DIST_DIR to the folder that contains index.html and data/.",
      "Example: VOCAB_DIST_DIR=swedish-vocab-site/dist node scripts/validate-vocabulary.mjs",
    ].join("\n"),
  );
}
