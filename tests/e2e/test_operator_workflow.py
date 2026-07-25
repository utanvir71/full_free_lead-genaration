from playwright.sync_api import sync_playwright
from sqlalchemy import update

from app.db import schema
from tests.integration.test_full_pipeline import seed_completed_run


def test_operator_can_review_a_completed_run_in_local_browser(
    live_app, tmp_path
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(f"{live_app.base_url}/runs")
        page.get_by_label("State").select_option("TX")
        page.get_by_label("City").select_option("Austin", timeout=5_000)
        page.get_by_label("Candidate limit").fill("2")
        page.get_by_role("button", name="Start research").click(no_wait_after=True)
        page.wait_for_url("**/runs/*", timeout=5_000)
        run_id = page.url.rsplit("/", maxsplit=1)[-1]
        page.reload()
        assert page.get_by_text("running", exact=True).is_visible()
        seed_completed_run(live_app.app.state.engine, run_id, tmp_path)
        with live_app.app.state.engine.begin() as connection:
            connection.execute(
                update(schema.runs)
                .where(schema.runs.c.id == run_id)
                .values(status="interrupted")
            )

        page.reload()
        assert page.get_by_text("interrupted", exact=True).is_visible()
        assert page.get_by_text("Qualified", exact=True).is_visible()
        page.get_by_role("link", name="Review leads").click(timeout=1_000)
        page.get_by_role("link", name="Elm House").click()
        assert page.get_by_text("events@elm.example").is_visible()
        page.get_by_role("textbox").fill("Review before outreach")
        page.get_by_role("button", name="Add note").click()
        assert page.get_by_text("Review before outreach").is_visible()
        page.locator("select[name=status]").select_option("draft_ready")
        page.get_by_role("button", name="Update status").click()
        assert page.get_by_text("Status: draft_ready").is_visible()
        page.goto(f"{live_app.base_url}/runs/{run_id}")
        with page.expect_download() as qualified_download:
            page.get_by_role("link", name="Download qualified CSV").click()
        assert qualified_download.value.suggested_filename == "qualified_leads.csv"
        with page.expect_download() as rejected_download:
            page.get_by_role("link", name="Download rejected CSV").click()
        assert rejected_download.value.suggested_filename == "rejected_leads.csv"
        page.get_by_role("link", name="Review drafts").click()
        page.get_by_role("link", name="Elm House").click()
        assert page.get_by_role("button", name="Copy locally").is_visible()
        assert not page.get_by_text("Send", exact=True).is_visible()
        browser.close()
