#!/usr/bin/env python3
"""
d2r-qa-harness.py
Automated X11 QA Smoke-Test Harness for Diablo II: Resurrected (-mod custom -txt).
Always cleans up / closes D2R.exe at the end of a test run so the game window never
remains open blocking the user's terminal.
"""
import argparse
import ctypes
import os
import re
import subprocess
import sys
import time

os.environ.setdefault("DISPLAY", ":0")


class X11Controller:
    def __init__(self):
        self.x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        self.xtst = ctypes.cdll.LoadLibrary("libXtst.so.6")

        self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.x11.XOpenDisplay.restype = ctypes.c_void_p

        self.x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self.x11.XFlush.argtypes = [ctypes.c_void_p]

        self.x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.x11.XKeysymToKeycode.restype = ctypes.c_ubyte

        self.x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        self.x11.XStringToKeysym.restype = ctypes.c_ulong

        self.x11.XSetInputFocus.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        self.x11.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]

        self.xtst.XTestFakeMotionEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        self.xtst.XTestFakeButtonEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        self.xtst.XTestFakeKeyEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_ulong,
        ]

        self.dpy = self.x11.XOpenDisplay(None)
        if not self.dpy:
            raise RuntimeError("Failed to open X11 display")

        # Install non-fatal X11 error handler so transient window close/recreate doesn't abort Python
        ERR_HANDLER = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
        def _ignore_x_err(dpy, err):
            return 0
        self._err_cb = ERR_HANDLER(_ignore_x_err)
        self.x11.XSetErrorHandler(self._err_cb)

    def close(self):
        if self.dpy:
            self.x11.XCloseDisplay(self.dpy)
            self.dpy = None

    def find_d2r_window(self):
        """Return (win_id_int, x, y, width, height) for the main D2R window, or None."""
        out = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True, errors="replace")
        best = None
        for line in out.splitlines():
            if "Diablo II: Resurrected" in line:
                m = re.search(
                    r"(0x[0-9a-fA-F]+)\s+\"Diablo II: Resurrected\".*?(\d+)x(\d+)\+(-?\d+)\+(-?\d+)\s+\+(-?\d+)\+(-?\d+)",
                    line,
                )
                if m:
                    win_id = int(m.group(1), 16)
                    w = int(m.group(2))
                    h = int(m.group(3))
                    abs_x = int(m.group(6))
                    abs_y = int(m.group(7))
                    if w >= 640 and h >= 480:
                        if best is None or (w * h) > (best[3] * best[4]):
                            best = (win_id, abs_x, abs_y, w, h)
        return best

    def focus_window(self, win_id):
        self.x11.XRaiseWindow(self.dpy, win_id)
        self.x11.XSetInputFocus(self.dpy, win_id, 2, 0)
        self.x11.XFlush(self.dpy)
        time.sleep(0.05)

    def move_mouse_abs(self, x, y):
        self.xtst.XTestFakeMotionEvent(self.dpy, -1, int(x), int(y), 0)
        self.x11.XFlush(self.dpy)
        time.sleep(0.05)

    def click_abs(self, x, y, button=1, hold=0.06):
        self.move_mouse_abs(x, y)
        time.sleep(0.05)
        self.xtst.XTestFakeButtonEvent(self.dpy, button, 1, 0)
        self.x11.XFlush(self.dpy)
        time.sleep(hold)
        self.xtst.XTestFakeButtonEvent(self.dpy, button, 0, 0)
        self.x11.XFlush(self.dpy)
        time.sleep(0.05)

    def click_rel(self, win_info, rx, ry, button=1):
        win_id, wx, wy, ww, wh = win_info
        self.focus_window(win_id)
        tx = wx + int(ww * rx)
        ty = wy + int(wh * ry)
        self.click_abs(tx, ty, button=button)

    def press_key(self, keysym_name, hold=0.06):
        ks = self.x11.XStringToKeysym(keysym_name.encode("ascii"))
        if not ks:
            raise ValueError(f"Unknown keysym: {keysym_name}")
        kc = self.x11.XKeysymToKeycode(self.dpy, ks)
        self.xtst.XTestFakeKeyEvent(self.dpy, kc, 1, 0)
        self.x11.XFlush(self.dpy)
        time.sleep(hold)
        self.xtst.XTestFakeKeyEvent(self.dpy, kc, 0, 0)
        self.x11.XFlush(self.dpy)
        time.sleep(0.05)

    def screenshot(self, win_info, out_path):
        win_id, wx, wy, ww, wh = win_info
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        subprocess.check_call(["maim", "-i", str(win_id), out_path])
        return out_path


def kill_d2r(ctrl=None):
    subprocess.run(["pkill", "-9", "-f", "[B]lizzardError.exe"], check=False)
    subprocess.run(["pkill", "-9", "-f", "[D]2R.exe"], check=False)
    if ctrl is not None:
        for _ in range(20):
            if ctrl.find_d2r_window() is None:
                break
            time.sleep(0.25)


def check_crash_or_missing_window(ctrl):
    res = subprocess.run(["pgrep", "-f", "[B]lizzardError.exe"], stdout=subprocess.DEVNULL)
    if res.returncode == 0:
        kill_d2r(ctrl)
        raise RuntimeError("ABORT: BlizzardError.exe crash dialog detected (killed immediately before any clicks)")
    win = ctrl.find_d2r_window()
    if win is None:
        kill_d2r(ctrl)
        raise RuntimeError("ABORT: D2R window disappeared unexpectedly (killed cleanly)")
    return win


def launch_d2r_and_wait_window(ctrl, timeout=35):
    kill_d2r(ctrl)
    time.sleep(1.0)
    log_f = open("/tmp/d2r-mod-qa.log", "w")
    subprocess.Popen(
        ["/home/grant/games/d2r/bin/d2r-mod"],
        stdout=log_f,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    t0 = time.time()
    while time.time() - t0 < timeout:
        win = ctrl.find_d2r_window()
        if win:
            return win
        time.sleep(1.0)
    raise RuntimeError("Timed out waiting for Diablo II: Resurrected window to appear")


def run_smoke_test(ctrl, out_dir, step_name, enter_game=True, offline_tab_pos=(0.905, 0.088)):
    """
    Single self-contained QA run:
      1. Launches d2r-mod
      2. Clicks past splash logos & title gate to reach Character Selection
      3. Captures <step_name>_char_screen.png
      4. If enter_game=True, clicks Offline tab, presses Return to load TESTER into Act 1 Rogue Encampment,
         waits for .txt compilation & loading door, and captures <step_name>_ingame.png
      5. Always kills D2R.exe before returning so the user's screen is never left blocked.
    """
    os.makedirs(out_dir, exist_ok=True)
    try:
        print(f"[QA] Launching D2R for step '{step_name}'...")
        win = launch_d2r_and_wait_window(ctrl)
        print(f"[QA] Found D2R window: id={hex(win[0])} pos=({win[1]},{win[2]}) size={win[3]}x{win[4]}")

        # Wait 3s for initial window setup, then click past splash screens & title gate
        time.sleep(3.0)
        for i in range(9):
            win = check_crash_or_missing_window(ctrl)
            ctrl.click_rel(win, 0.50, 0.50)
            time.sleep(1.5)

        time.sleep(2.5)
        win = check_crash_or_missing_window(ctrl)
        char_shot = os.path.join(out_dir, f"{step_name}_char_screen.png")
        ctrl.screenshot(win, char_shot)
        print(f"[QA] Saved character screen screenshot: {char_shot}")

        if enter_game:
            # Press Return (and click Play at bottom center 0.50, 0.895) to enter game with TESTER
            print("[QA] Loading TESTER into Rogue Encampment (compiling .txt tables)...")
            win = check_crash_or_missing_window(ctrl)
            ctrl.click_rel(win, 0.50, 0.895)
            ctrl.focus_window(win[0])
            ctrl.press_key("Return")
            for _ in range(10):
                time.sleep(1.0)
                win = check_crash_or_missing_window(ctrl)

            ingame_shot = os.path.join(out_dir, f"{step_name}_ingame.png")
            ctrl.screenshot(win, ingame_shot)
            print(f"[QA] Saved in-game screenshot: {ingame_shot}")
    finally:
        print("[QA] Closing D2R.exe cleanly so terminal focus is restored...")
        kill_d2r()
        time.sleep(1.0)


def main():
    parser = argparse.ArgumentParser(description="D2R X11 QA Harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="Print D2R window info")

    p_shot = sub.add_parser("screenshot", help="Take screenshot of D2R window")
    p_shot.add_argument("out", help="Output PNG path")

    p_click = sub.add_parser("click", help="Click relative coordinates (0.0-1.0) in D2R window")
    p_click.add_argument("rx", type=float)
    p_click.add_argument("ry", type=float)
    p_click.add_argument("--button", type=int, default=1)

    p_key = sub.add_parser("key", help="Send key press to D2R window")
    p_key.add_argument("keysym", help="X11 keysym name (e.g. Return, space, Escape)")

    p_smoke = sub.add_parser("smoke-test", help="Full launch -> char screen -> enter game -> screenshot -> exit cycle")
    p_smoke.add_argument("step_name", help="Step identifier for screenshot filenames")
    p_smoke.add_argument(
        "--out-dir",
        default="/home/grant/.gemini/antigravity-cli/brain/a827b712-52be-4484-bbf4-3754fc7460e6/scratch",
        help="Directory to write screenshots",
    )
    p_smoke.add_argument("--char-screen-only", action="store_true", help="Stop after capturing character screen")
    p_smoke.add_argument("--offline-rx", type=float, default=0.905, help="Relative X of Offline tab")
    p_smoke.add_argument("--offline-ry", type=float, default=0.088, help="Relative Y of Offline tab")

    args = parser.parse_args()
    ctrl = X11Controller()
    try:
        if args.cmd == "smoke-test":
            run_smoke_test(
                ctrl,
                args.out_dir,
                args.step_name,
                enter_game=not args.char_screen_only,
                offline_tab_pos=(args.offline_rx, args.offline_ry),
            )
            return

        win = ctrl.find_d2r_window()
        if not win:
            print("ERROR: Diablo II: Resurrected window not found", file=sys.stderr)
            sys.exit(2)
        if args.cmd == "info":
            print(f"win_id={hex(win[0])} x={win[1]} y={win[2]} w={win[3]} h={win[4]}")
        elif args.cmd == "screenshot":
            ctrl.screenshot(win, args.out)
            print(f"Saved screenshot to {args.out}")
        elif args.cmd == "click":
            ctrl.click_rel(win, args.rx, args.ry, button=args.button)
            print(f"Clicked relative ({args.rx:.3f}, {args.ry:.3f})")
        elif args.cmd == "key":
            ctrl.focus_window(win[0])
            ctrl.press_key(args.keysym)
            print(f"Pressed key {args.keysym}")
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
