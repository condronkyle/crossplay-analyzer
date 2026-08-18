#!/usr/bin/env python3

import base64
import functools
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import Error, sync_playwright


ROOT = Path(__file__).resolve().parent

FIXTURES = {
    "test_board.png": {
        "grid": [
            "...............",
            "...............",
            "...............",
            "......VAT....W.",
            ".......MACHINES",
            "..........E...O",
            "..........X...B",
            "......GOONEY..E",
            "........PURE..R",
            "..............I",
            "..............N",
            "..............G",
            "...............",
            "...............",
            "...............",
        ],
        "scores": ("108", "130"),
        "rack": "WLSAPDI",
        "tiles": "31",
        "words": 12,
    },
    "IMG_3046.png": {
        "grid": [
            "...............",
            "...............",
            "...............",
            ".......G.......",
            ".....GOAT......",
            ".......P..F....",
            ".......E..A....",
            ".......DUCTAL..",
            "..........H....",
            "..........E....",
            "..........R....",
            "........PLEATED",
            "..........D....",
            "...............",
            "...............",
        ],
        "scores": ("43", "93"),
        "rack": "G",
        "tiles": "26",
        "words": 5,
    },
    "IMG_3047.png": {
        "grid": [
            "...........M..T",
            "...........A.EH",
            "......Q....N.WE",
            "GRIP.GUTTERY..I",
            "...O..A.E...F.N",
            "...LINY.E..WEDS",
            "...O....M.BIZE.",
            "...SEI.JIHAD.T.",
            "........N.TE.A.",
            "........G.H..I.",
            ".............L.",
            "...........PASS",
            "...........A...",
            ".......CAB.R...",
            "........LOCKER.",
        ],
        "scores": ("235", "285"),
        "rack": "DUOONES",
        "tiles": "73",
        "words": 26,
    },
    "IMG_3048.png": {
        "grid": [
            "...K....POCO...",
            "..TEMPERED.....",
            "...N....TAUGHT.",
            "FEATHERS.......",
            "....I..A.......",
            "....V..B..Z....",
            ".VINE.DE..O....",
            ".....JARGOON...",
            "......I...MOI..",
            "L...CURB.......",
            "O.....YA...QIS.",
            "A......L.WAITER",
            "D...HAULIERS.X.",
            "SIXTEEN......Y.",
            "...AW.SELFED...",
        ],
        "scores": ("407", "412"),
        "rack": "--",
        "tiles": "96",
        "words": 35,
    },
}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class BrowserPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=ROOT)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(headless=True)
        except Error:
            cls.browser = cls.playwright.chromium.launch(channel="chrome", headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join()

    def open_page(self):
        page = self.browser.new_page()
        page_errors = []
        console_messages = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("console", lambda message: console_messages.append(message.text))
        page.goto(self.base_url, wait_until="domcontentloaded")
        return page, page_errors, console_messages

    def wait_for_analysis(self, page):
        page.locator("#analyzeBtn").click()
        page.wait_for_function(
            "document.getElementById('status').classList.contains('done') || "
            "document.getElementById('status').classList.contains('error')",
            timeout=120_000,
        )
        self.assertEqual(page.locator("#status").get_attribute("class"), "done")

    def rendered_grid(self, page):
        return page.eval_on_selector_all(
            "#boardContainer table.board tr:not(:first-child)",
            """rows => rows.map(row => [...row.querySelectorAll('td')]
              .map(cell => cell.classList.contains('empty') ? '.' : cell.textContent.trim())
              .join(''))""",
        )

    def test_all_fixtures(self):
        for fixture, expected in FIXTURES.items():
            with self.subTest(fixture=fixture):
                page, page_errors, console_messages = self.open_page()
                page.locator("#imageUrlInput").fill(f"{self.base_url}/{fixture}")
                self.wait_for_analysis(page)

                self.assertEqual(self.rendered_grid(page), expected["grid"])
                self.assertEqual(page.locator("#p1Score").text_content(), expected["scores"][0])
                self.assertEqual(page.locator("#p2Score").text_content(), expected["scores"][1])
                self.assertEqual(page.locator("#rackDisplay").text_content(), expected["rack"])
                self.assertEqual(page.locator("#tileCount").text_content(), expected["tiles"])
                self.assertEqual(page.locator("#wordsContainer tbody tr").count() - 1, expected["words"])
                self.assertEqual(page_errors, [])

                if fixture == "IMG_3048.png":
                    self.assertTrue(page.locator("#kibitzBtn").evaluate("el => el.classList.contains('hidden')"))

                if fixture == "test_board.png":
                    page.evaluate(
                        "window.__quackleStatuses = []; "
                        "new MutationObserver(() => window.__quackleStatuses.push("
                        "document.getElementById('engineStatus').textContent))"
                        ".observe(document.getElementById('engineStatus'), "
                        "{childList: true, subtree: true})"
                    )
                    page.locator("#kibitzBtn").click()
                    page.wait_for_function(
                        "document.getElementById('engineStatus').textContent.includes('running 50 rounds') || "
                        "document.getElementById('engineStatus').textContent.startsWith('Error:')",
                        timeout=120_000,
                    )
                    running_status = page.locator("#engineStatus").text_content()
                    self.assertIn("running 50 rounds", running_status)
                    self.assertTrue(page.locator("#kibitzBtn").is_disabled())
                    page.evaluate(
                        "window.__quackleHeartbeat = false; "
                        "setTimeout(() => { window.__quackleHeartbeat = true; }, 100)"
                    )
                    page.wait_for_function("window.__quackleHeartbeat", timeout=5_000)
                    page.wait_for_function(
                        "document.getElementById('engineStatus').textContent.startsWith('Found ') || "
                        "document.getElementById('engineStatus').textContent.startsWith('Error:')",
                        timeout=120_000,
                    )
                    engine_status = page.locator("#engineStatus").text_content()
                    self.assertTrue(engine_status.startswith("Found "), engine_status)
                    self.assertTrue(any(
                        "running 50 rounds" in status
                        for status in page.evaluate("window.__quackleStatuses")
                    ))
                    self.assertEqual(page.locator("#movesContainer tbody tr").count() - 1, 15)
                    win_cells = page.locator("#movesContainer tbody tr:not(:first-child) td:nth-child(4)")
                    self.assertEqual(win_cells.count(), 15)
                    for index in range(win_cells.count()):
                        cell = win_cells.nth(index)
                        self.assertRegex(cell.text_content(), r"^(100|[0-9]{1,2})\.\d%$")
                        self.assertEqual(cell.get_attribute("data-samples"), "50")
                    self.assertIn("Simulated 50 rounds per move", engine_status)
                    self.assertIn("750 playouts total", engine_status)
                    self.assertFalse(page.locator("#kibitzBtn").is_disabled())
                    self.assertFalse(any("bogowin heuristic" in message for message in console_messages))

                page.close()

    def test_board_change_clears_simulation_state(self):
        page, page_errors, _ = self.open_page()
        page.locator("#imageUrlInput").fill(f"{self.base_url}/test_board.png")
        self.wait_for_analysis(page)
        page.locator("#kibitzBtn").click()
        page.wait_for_function(
            "document.getElementById('engineStatus').textContent.includes('running 50 rounds') || "
            "document.getElementById('engineStatus').textContent.startsWith('Error:')",
            timeout=120_000,
        )
        self.assertIn("running 50 rounds", page.locator("#engineStatus").text_content())

        page.locator("#imageUrlInput").fill(f"{self.base_url}/IMG_3046.png")
        self.wait_for_analysis(page)
        expected_status = "Board ready. Run Quackle to estimate win percentages."
        self.assertEqual(page.locator("#engineStatus").text_content(), expected_status)
        self.assertTrue(page.locator("#movesContainer").evaluate("el => el.classList.contains('hidden')"))
        self.assertEqual(page.locator("#movesContainer").text_content(), "")
        self.assertFalse(page.locator("#kibitzBtn").is_disabled())
        page.wait_for_timeout(2_500)
        self.assertEqual(page.locator("#engineStatus").text_content(), expected_status)
        self.assertEqual(page.locator("#movesContainer").text_content(), "")
        self.assertEqual(page_errors, [])
        page.close()

    def test_manual_board_simulation(self):
        page, page_errors, console_messages = self.open_page()
        page.goto(f"{self.base_url}/manual.html", wait_until="domcontentloaded")
        page.evaluate("loadSample()")
        page.locator("#kibitzBtn").click()
        page.wait_for_function(
            "document.getElementById('engineStatus').textContent.includes('running 50 rounds') || "
            "document.getElementById('engineStatus').textContent.startsWith('Error:')",
            timeout=120_000,
        )
        self.assertIn("running 50 rounds", page.locator("#engineStatus").text_content())
        self.assertTrue(page.locator("#kibitzBtn").is_disabled())
        page.evaluate(
            "window.__manualHeartbeat = false; "
            "setTimeout(() => { window.__manualHeartbeat = true; }, 100)"
        )
        page.wait_for_function("window.__manualHeartbeat", timeout=5_000)
        page.wait_for_function(
            "document.getElementById('engineStatus').textContent.startsWith('Found ') || "
            "document.getElementById('engineStatus').textContent.startsWith('Error:')",
            timeout=120_000,
        )
        engine_status = page.locator("#engineStatus").text_content()
        self.assertTrue(engine_status.startswith("Found "), engine_status)
        self.assertIn("Simulated 50 rounds per move", engine_status)
        self.assertIn("750 playouts total", engine_status)
        win_cells = page.locator("#movesContainer td[data-samples]")
        self.assertEqual(win_cells.count(), 15)
        for index in range(win_cells.count()):
            cell = win_cells.nth(index)
            self.assertRegex(cell.text_content(), r"^(100|[0-9]{1,2})\.\d%$")
            self.assertEqual(cell.get_attribute("data-samples"), "50")
        self.assertFalse(page.locator("#kibitzBtn").is_disabled())
        self.assertFalse(any("bogowin heuristic" in message for message in console_messages))
        self.assertEqual(page_errors, [])
        page.close()

    def test_engine_load_retry(self):
        page, page_errors, _ = self.open_page()
        attempts = {"count": 0}

        def fail_first_worker_request(route):
            attempts["count"] += 1
            if attempts["count"] == 1:
                route.abort()
            else:
                route.continue_()

        page.route("**/quackle-worker.js", fail_first_worker_request)
        page.locator("#imageUrlInput").fill(f"{self.base_url}/test_board.png")
        self.wait_for_analysis(page)
        page.locator("#kibitzBtn").click()
        page.wait_for_function(
            "document.getElementById('engineStatus').textContent.includes('Engine load failed')",
            timeout=10_000,
        )
        self.assertFalse(page.locator("#kibitzBtn").is_disabled())
        self.assertTrue(page.evaluate("quackleWorker === null"))

        page.locator("#kibitzBtn").click()
        page.wait_for_function(
            "document.getElementById('engineStatus').textContent.startsWith('Found ') || "
            "document.getElementById('engineStatus').textContent.startsWith('Error:')",
            timeout=120_000,
        )
        engine_status = page.locator("#engineStatus").text_content()
        self.assertTrue(engine_status.startswith("Found "), engine_status)
        self.assertEqual(attempts["count"], 2)
        self.assertEqual(page_errors, [])
        page.close()

    def test_engine_rejects_impossible_tile_distribution(self):
        page, page_errors, _ = self.open_page()
        result = page.evaluate(
            """async () => {
              if (!await loadQuackleEngine()) throw new Error('Engine did not load');
              return callQuackleWorker('simulateKibitz', {
                gridJson: JSON.stringify(Array(15).fill('AAAAAAAAAAAAAAA')),
                rack: 'A', playerScore: 0, opponentScore: 0,
                numMoves: 15, iterations: 1
              });
            }"""
        )
        self.assertFalse(result["simulated"])
        self.assertEqual(result["iterationsCompleted"], 0)
        self.assertIn("more tiles than the Crossplay distribution", result["error"])
        self.assertEqual(page_errors, [])
        page.close()

    def test_drop_input(self):
        page, page_errors, _ = self.open_page()
        fixture = "test_board.png"
        encoded = base64.b64encode((ROOT / fixture).read_bytes()).decode("ascii")
        page.evaluate(
            """({name, encoded}) => {
              const bytes = Uint8Array.from(atob(encoded), value => value.charCodeAt(0));
              const file = new File([bytes], name, {type: 'image/png'});
              const transfer = new DataTransfer();
              transfer.items.add(file);
              document.getElementById('dropZone').dispatchEvent(new DragEvent('drop', {
                bubbles: true,
                cancelable: true,
                dataTransfer: transfer
              }));
            }""",
            {"name": fixture, "encoded": encoded},
        )
        page.wait_for_function("document.getElementById('status').textContent.includes('Image ready')")
        self.wait_for_analysis(page)
        self.assertEqual(page.locator("#tileCount").text_content(), "31")
        self.assertEqual(page_errors, [])
        page.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
