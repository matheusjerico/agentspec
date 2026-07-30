import { expect, test } from "@playwright/test";

const baseURL = process.env.FRONTEND_BASE_URL ?? "http://127.0.0.1:5173";
const swapCase = (value: string) =>
  [...value]
    .map((character) =>
      character === character.toUpperCase()
        ? character.toLowerCase()
        : character.toUpperCase(),
    )
    .join("");

test.use({ baseURL });

test("TaskFlow browser behavior and accessible states", async ({ page }) => {
  const marker = `Contract ${Date.now()}`;

  await page.goto("/");
  await expect(page.getByRole("heading", { name: /taskflow/i }).first()).toBeVisible();

  const title = page.getByLabel(/title/i);
  await expect(title).toBeVisible();
  await expect(page.getByLabel(/description/i)).toBeVisible();
  await expect(page.getByLabel(/filter.*status|status.*filter/i)).toBeVisible();

  await title.fill("   ");
  await page.getByRole("button", { name: /add|create|save/i }).click();
  await expect(page.getByText(/title.*required|enter.*title|cannot be blank/i)).toBeVisible();

  await title.fill(marker);
  await page.getByLabel(/description/i).fill("Initial browser description");
  await page.getByRole("button", { name: /add|create|save/i }).click();
  const task = page.getByText(marker, { exact: true });
  await expect(task).toBeVisible();

  const taskItems = page.getByRole("listitem");
  const taskIndex = (await taskItems.allTextContents()).findIndex((text) =>
    text.includes(marker),
  );
  expect(taskIndex).toBeGreaterThanOrEqual(0);
  const taskRegion = taskItems.nth(taskIndex);
  await taskRegion.getByRole("button", { name: /edit/i }).click();
  await taskRegion.getByLabel(/description/i).fill("Edited browser description");
  await taskRegion.getByRole("button", { name: /save|update/i }).click();
  await expect(taskRegion.getByText("Edited browser description")).toBeVisible();
  await taskRegion.getByLabel(/status/i).selectOption("doing");
  await page.getByLabel(/filter.*status|status.*filter/i).selectOption("doing");
  await expect(task).toBeVisible();
  await page.getByLabel(/search/i).fill(swapCase(marker));
  await expect(task).toBeVisible();

  await taskRegion.getByRole("button", { name: /delete/i }).click();
  const confirmDelete = taskRegion.getByRole("button", { name: /confirm.*delete/i });
  if (await confirmDelete.isVisible().catch(() => false)) {
    await confirmDelete.click();
  }
  await expect(task).toHaveCount(0);
});

test("TaskFlow exposes loading and request-failure feedback", async ({ page }) => {
  let releaseResponse: (() => void) | undefined;
  const responseReleased = new Promise<void>((resolve) => {
    releaseResponse = resolve;
  });
  await page.route(/\/tasks(?:\?.*)?$/, async (route) => {
    await responseReleased;
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.goto("/");
  await expect(page.getByText(/loading/i)).toBeVisible();
  releaseResponse?.();
  await expect(page.getByText(/no tasks|empty|nothing here/i)).toBeVisible();

  await page.unroute(/\/tasks(?:\?.*)?$/);
  await page.route(/\/tasks(?:\?.*)?$/, (route) => route.abort("failed"));
  await page.reload();
  await expect(page.getByText(/error|failed|try again|unavailable/i)).toBeVisible();
});
