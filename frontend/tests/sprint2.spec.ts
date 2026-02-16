import { expect, test } from "@playwright/test"
import { createUser } from "./utils/privateApi"
import { randomEmail } from "./utils/random"
import { logInUser } from "./utils/user"

test.describe("Sprint 2 flow", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("user can complete onboarding and log an action", async ({ page }) => {
    const email = randomEmail()
    const password = "sprint2password"
    await createUser({ email, password })

    await logInUser(page, email, password)
    await page.goto("/")

    await expect(
      page.getByRole("heading", { name: "Complete your onboarding" }),
    ).toBeVisible()
    await page.getByTestId("onboarding-username-input").fill("sprint2_frontend")
    await page.getByTestId("onboarding-state-input").fill("TX")
    await page.getByTestId("onboarding-district-input").fill("01")

    // Enable weekend participation so the action list is available every day.
    await page.getByTestId("onboarding-weekday-sat").click()
    await page.getByTestId("onboarding-weekday-sun").click()

    await page.getByTestId("onboarding-submit").click()
    await expect(page.getByText("Onboarding completed")).toBeVisible()
    await expect(page.getByText("Profile Summary")).toBeVisible()

    await page.getByRole("link", { name: "Go To Today's Actions" }).click()
    await expect(
      page.getByRole("heading", { name: "Today's Actions" }),
    ).toBeVisible()

    const actionButtons = page.getByRole("button", { name: "Log Completed" })
    await expect(actionButtons.first()).toBeVisible()
    await actionButtons.first().click()
    await expect(page.getByText("Action logged successfully")).toBeVisible()
  })

  test("user can update visibility and privacy controls", async ({ page }) => {
    const email = randomEmail()
    const password = "sprint2privacy"
    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/")
    await page.getByTestId("onboarding-username-input").fill("sprint2_privacy")
    await page.getByTestId("onboarding-weekday-sat").click()
    await page.getByTestId("onboarding-weekday-sun").click()
    await page.getByTestId("onboarding-submit").click()
    await expect(page.getByText("Onboarding completed")).toBeVisible()

    await page.goto("/settings")
    await page.getByRole("tab", { name: "Privacy" }).click()

    await page.getByTestId("privacy-visibility-select").click()
    await page.getByRole("option", { name: "Public (opt-in)" }).click()
    await expect(page.getByText("Visibility mode updated")).toBeVisible()

    await page.getByTestId("privacy-show-on-leaderboard").click()
    await expect(page.getByText("Privacy settings updated")).toBeVisible()
  })
})
