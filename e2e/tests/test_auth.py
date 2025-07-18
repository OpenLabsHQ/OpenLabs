from playwright.sync_api import Page, expect


def test_navigate_to_login(page: Page, app_url: str) -> None:
    page.goto(app_url)

    login_link = page.get_by_role("link", name="Login")

    login_link.click()

    expect(page).to_have_url(f"{app_url}/login")


def test_navigate_to_signup(page: Page, app_url: str) -> None:
    page.goto(app_url)

    page.get_by_role("link", name="Sign Up").click()

    expect(page).to_have_url(f"{app_url}/signup")
