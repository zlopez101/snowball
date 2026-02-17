import { expect, test } from "@playwright/test"

import { createUser } from "./utils/privateApi"
import { randomEmail } from "./utils/random"
import { logInUser, logOutUser } from "./utils/user"

test.describe("Sprint 4 referral attribution flow", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("recruiter sees assist metrics after referred user signs up and claims code", async ({
    page,
  }) => {
    const recruiterEmail = randomEmail()
    const recruiterPassword = "sprint4recruiter"
    await createUser({ email: recruiterEmail, password: recruiterPassword })
    await logInUser(page, recruiterEmail, recruiterPassword)

    await page.goto("/referrals")
    await page.getByTestId("create-referral-link").click()
    await expect(page.getByText("Referral link created")).toBeVisible()
    const code = (await page.getByTestId("latest-referral-code").innerText()).trim()
    expect(code.length).toBeGreaterThan(5)

    await logOutUser(page)

    const referredEmail = randomEmail()
    const referredPassword = "sprint4referred"
    await createUser({ email: referredEmail, password: referredPassword })
    await logInUser(page, referredEmail, referredPassword)
    await page.goto("/referrals")
    await page.getByTestId("claim-referral-code-input").fill(code)
    await page.getByTestId("claim-referral-code-button").click()
    await expect(page.getByText("Referral claimed")).toBeVisible()

    await logOutUser(page)
    await logInUser(page, recruiterEmail, recruiterPassword)
    await page.goto("/referrals")

    const recruitedUsersValue = await page.getByTestId("recruited-users-value").innerText()
    expect(Number.parseInt(recruitedUsersValue, 10)).toBeGreaterThan(0)
  })
})
