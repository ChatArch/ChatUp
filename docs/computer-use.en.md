# Linux Computer Use

`chatup computer-use` prepares managed `cua-driver` entrypoints for an X11 desktop owned by the same ordinary user. The installer currently supports Debian/Ubuntu Linux x86_64 with X11. It does not claim Wayland, other distributions, or automatic remote desktop routing.

## Preview before explicit apply

```bash
chatup computer-use
chatup computer-use --sudo --dry-run
chatup computer-use --display :20 --xauthority "$XAUTHORITY"
chatup computer-use --state "$CHATARCH_HOME/computer-use/run/desktop.env.json"
chatup computer-use --sudo
```

The bare command and `--sudo --dry-run` only read local OS facts, X11 sockets, and same-user state, then return a JSON plan. They do not probe sudo, create directories, download, start processes, or load model credentials. Only `--sudo` without `--dry-run` applies. Pass `--display` together with `--xauthority`; `--state` selects same-user desktop metadata instead. `--home` explicitly selects a managed root; the effective ChatEnv/`CHATARCH_HOME` is the default.

The plan includes hostname/UID, desktop selection, proposed packages, Chrome/driver reuse, entrypoint paths, and security and energy effects. Existing same-user X11 state or the current X11 session is preferred. Explicitly selecting a connectable same-user desktop attaches without rewriting, restarting, or enabling its owner's service. With no reusable desktop, ChatUp plans a separate Xfce/TigerVNC user session. Its password-authenticated VNC listens on loopback only; it does not add a display manager, upgrade the GPU/OS, or change firewall/public ports. An owned session consumes resources while running and disables screen blanking and DPMS; its own user service controls its lifecycle.

## Managed runtime and entrypoints

Apply places a dedicated venv, official PyPI `cua-driver==0.36.0`, private target metadata, and separate `mcp`, `chrome`, `terminal`, and `status` entrypoints under `computer-use/chatup-<version>/` in the effective ChatArch home. If a same-user dedicated Computer Use venv already has a verified compatible driver, the new namespace links to that venv without modifying the existing runtime. A newly managed desktop also gets an owned `desktop` entrypoint and user service. The JSON result gives the actual absolute paths. Run its `entrypoints.status` to inspect the target, display, entrypoints, and readiness. State and VNC credentials are user-private. Before starting a client, an entrypoint checks hostname, UID, Xauthority, and the live X11 socket; stale targets refuse without falling back to the caller's screen.

Installed regular Google Chrome is verified and reused without automatic upgrade or launch. If absent, apply uses the existing `setup_desktop_app('chrome')` installation contract. The `chrome` side entry opens a window with the current user's default profile only when explicitly invoked. It does not use Chrome for Testing, a custom user-data-dir, or copied cookies/passwords, and it does not automate login, default-browser consent, or telemetry opt-in. The MCP entry uses a private driver-only HOME under the managed runtime to direct the driver's home state there; Chrome and terminal entries retain the ordinary user's HOME. Existing global driver state is not migrated. Driver children receive a restricted environment without provider or installer secrets. The vendor's actual state path still needs live acceptance.

A remote Agent that needs MCP must be configured separately with an explicit SSH execution target and the returned absolute `entrypoints.mcp` path. ChatUp does not edit Hermes or other Agent configuration or set global `HERMES_CUA_DRIVER_CMD` or terminal backend values. **Installing ChatUp does not fix Hermes's per-topic SSH binding gap that can leave default screenshot capture on the controller.** That route needs its own Hermes fix and acceptance. The installer and driver prepare native screenshot/input execution; image understanding belongs to the Agent/model, DOM access is a separate authorized capability, and authenticated state comes from the same user's existing Chrome profile. These are distinct capabilities.
