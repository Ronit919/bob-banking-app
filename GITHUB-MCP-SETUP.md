# GitHub MCP Setup for Demo Participants

This guide connects Bob to GitHub so you can use GitHub tools (search repos, create files, open PRs, etc.) during the demo session.

> **Who is this for?**  
> - ✅ **External / trial users** — public `github.com` account → follow this guide as-is  
> - ✅ **IBMers on `github.ibm.com`** — follow this guide but use [Step 2b](#step-2b--ibmers-on-githubibmcom) instead of Step 2a

---

## Before You Start — Know Your GitHub Username

You will need your exact GitHub username at Step 3. Find it by visiting your GitHub profile:

- Public GitHub: `https://github.com/<your-username>`
- IBM GitHub: `https://github.ibm.com/<your-username>`

**Write it down now** — you'll use it when asking Bob to list your repos.

---

## Prerequisites

**Node.js v18 or later** must be installed.  
→ Download: https://nodejs.org

Confirm it's available by running in a terminal:
```bash
node --version
```
You should see `v18.x.x` or higher. If not, install Node.js first before continuing.

---

## Step 1 — Generate a GitHub Personal Access Token

### For public `github.com` users

1. Go to: https://github.com/settings/tokens/new
2. **Token name:** `Bob Demo`
3. **Expiration:** `7 days`
4. **Scopes — tick these:**
   - `repo`
   - `read:user`
5. Click **Generate token**
6. **Copy the token immediately** — it won't be shown again

### For IBMers on `github.ibm.com`

1. Go to: `https://github.ibm.com/settings/tokens/new`
2. **Token name:** `Bob Demo`
3. **Expiration:** `7 days`
4. **Scopes — tick these:**
   - `repo`
   - `read:user`
5. Click **Generate token**
6. **Copy the token immediately**

---

## Step 2a — Configure Bob (public `github.com` users)

Open or create the file `.bob/mcp.json` in your project workspace and paste the following, replacing `<PASTE_YOUR_TOKEN_HERE>` with your token:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<PASTE_YOUR_TOKEN_HERE>"
      }
    }
  }
}
```

---

## Step 2b — Configure Bob (IBMers on `github.ibm.com`)

Open or create the file `.bob/mcp.json` and paste the following, replacing both placeholders:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<PASTE_YOUR_IBM_TOKEN_HERE>",
        "GITHUB_HOST": "https://github.ibm.com/api/v3"
      }
    }
  }
}
```

> The `GITHUB_HOST` variable points the MCP server at IBM's GitHub Enterprise API instead of public GitHub.

---

> ⚠️ **Keep your token private.** Do not commit `.bob/mcp.json` to any repository.  
> Add `.bob/mcp.json` to your `.gitignore` if it isn't already.

A ready-to-edit template is at [`docs/demo-setup/mcp-github-template.json`](./mcp-github-template.json).

---

## Step 3 — Verify the Connection

Bob hot-reloads the MCP config on save. After saving `.bob/mcp.json`:

1. Open the **MCP panel** in Bob (bottom status bar or Command Palette → *MCP: Show Servers*)
2. You should see **github** listed with a green connected status
3. Ask Bob:
   > *"List my GitHub repositories for username `<your-github-username>`"*

   Providing your username directly avoids any lookup errors.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `npx: command not found` | Node.js is not installed → https://nodejs.org |
| `Bad credentials` | Token was typed incorrectly or has expired — regenerate it |
| `cannot be searched / 422 error` | Wrong username supplied to Bob — double-check your GitHub profile URL |
| IBMer getting `404` or no results | Missing `GITHUB_HOST` env var in config — use Step 2b config |
| Server shows red / disconnected | Check `.bob/mcp.json` for typos or leftover placeholder text |
| No MCP panel visible | Bob needs a **workspace folder open** (File → Open Folder). MCP won't load in an empty window. |

---

## Cleanup After the Demo

Revoke the token so it can't be misused:
- Public GitHub: https://github.com/settings/tokens → delete `Bob Demo`
- IBM GitHub: `https://github.ibm.com/settings/tokens` → delete `Bob Demo`
