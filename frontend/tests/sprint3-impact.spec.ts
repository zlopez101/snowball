import { expect, test } from "@playwright/test"

import { createUser } from "./utils/privateApi"
import { randomEmail } from "./utils/random"
import { logInUser } from "./utils/user"

test.describe("Sprint 3 impact and privacy flow", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("user can view impact metrics and opt in to shareable card identity", async ({
    page,
  }) => {
    const email = randomEmail()
    const password = "sprint3password"
    const username = `sprint3_${Date.now()}`
    await createUser({ email, password })

    await logInUser(page, email, password)
    await page.goto("/")

    await page.getByTestId("onboarding-username-input").fill(username)
    await page.getByTestId("onboarding-state-input").fill("TX")
    await page.getByTestId("onboarding-district-input").fill("10")
    await page.getByTestId("onboarding-weekday-sat").click()
    await page.getByTestId("onboarding-weekday-sun").click()
    await page.getByTestId("onboarding-submit").click()
    await expect(page.getByText("Onboarding completed")).toBeVisible()

    await page.goto("/actions")
    await expect(page.getByRole("heading", { name: "Today's Actions" })).toBeVisible()
    await page.getByRole("button", { name: "Log Completed" }).first().click()
    await expect(page.getByText("Action logged successfully")).toBeVisible()

    await page.goto("/impact")
    await expect(page.getByRole("heading", { name: "Impact Dashboard" })).toBeVisible()
    await expect(page.getByTestId("impact-platform-total-card")).toBeVisible()
    await expect(page.getByTestId("impact-share-card")).toBeVisible()
    await expect(page.getByTestId("share-card-display-name")).toHaveText("Hidden")

    await page.goto("/settings")
    await page.getByRole("tab", { name: "Privacy" }).click()
    await page.getByTestId("privacy-visibility-select").click()
    await page.getByRole("option", { name: "Public (opt-in)" }).click()
    await expect(page.getByText("Visibility mode updated")).toBeVisible()
    await page.getByTestId("privacy-shareable-card").click()
    await expect(page.getByText("Privacy settings updated")).toBeVisible()

    await page.goto("/impact")
    await expect(page.getByTestId("share-card-display-name")).toHaveText(username)
  })
})
