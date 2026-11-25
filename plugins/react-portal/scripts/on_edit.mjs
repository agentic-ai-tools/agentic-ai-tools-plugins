// After-edit hook: run a tool on the edited file when its extension matches.
// usage: node on_edit.mjs .ts .tsx -- <command> [args...]   (the file path is appended)
// Claude Code sends tool_input.file_path, Cursor sends file_path. Exit 2 reports problems.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { extname } from "node:path";

const argv = process.argv.slice(2);
const sep = argv.indexOf("--");
const exts = new Set(argv.slice(0, sep));
const [cmd, ...args] = argv.slice(sep + 1);

let payload;
try {
  payload = JSON.parse(readFileSync(0, "utf8"));
} catch {
  process.exit(0);
}
const path = payload?.tool_input?.file_path ?? payload?.file_path;
if (!path || !exts.has(extname(path)) || !existsSync(path)) process.exit(0);

// Windows needs a shell to resolve npx.cmd; quote args so paths with spaces survive it.
const win = process.platform === "win32";
const argList = [...args, path].map((a) => (win ? `"${a}"` : a));
const result = spawnSync(cmd, argList, { encoding: "utf8", shell: win });
if (result.error) {
  console.error(`${cmd} is not on PATH; skipped`);
  process.exit(0);
}
if (result.status) {
  process.stderr.write((result.stdout ?? "") + (result.stderr ?? ""));
  process.exit(2);
}
