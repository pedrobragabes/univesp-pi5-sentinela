import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { writeFile } from 'node:fs/promises';

for (const [name, url] of [['readings', '/'], ['empty', '/empty-fixture']]) {
  test(`${name}: medições, acessibilidade e layout`, async ({ browser }, info) => {
    const context = await browser.newContext({ ...info.project.use });
    const page = await context.newPage();
    const errors = [];
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await page.goto(url);
    const layout = await page.evaluate(() => ({
      width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
      overflow: [...document.querySelectorAll('body *')].filter(el => !el.closest('.table-wrap') && el.getBoundingClientRect().right > innerWidth + 1)
        .map(el => ({ tag: el.tagName, class: el.className, right: el.getBoundingClientRect().right })),
    }));
    await writeFile(info.outputPath(`layout-${name}.json`), JSON.stringify(layout, null, 2));
    expect(layout.scrollWidth, JSON.stringify(layout)).toBeLessThanOrEqual(layout.width);
    const result = await new AxeBuilder({ page }).analyze();
    await writeFile(info.outputPath(`axe-${name}.json`), JSON.stringify(result.violations, null, 2));
    expect(result.violations).toEqual([]);
    if (name === 'readings') {
      const old = page.getByRole('article').filter({ hasText: 'sentinela-old-01' });
      await expect(old).toContainText('online');
      await expect(old).toContainText('medição antiga');
      await expect(page.getByRole('article').filter({ hasText: 'sentinela-recent-01' })).toContainText('medição recente');
      await expect(page.getByRole('article').filter({ hasText: 'sentinela-offline-01' })).toContainText('sem sinal');
      await expect(page.getByRole('article').filter({ hasText: 'sentinela-clock-' })).toContainText('relógio adiantado');
      expect(await page.locator('.table-wrap').evaluate(el => el.scrollWidth >= el.clientWidth)).toBe(true);
    } else {
      await expect(page.getByText('Nenhum sinal recebido.')).toBeVisible();
      await expect(page.getByText('Aguardando telemetria.')).toBeVisible();
    }
    await page.keyboard.press('Tab');
    await expect(page.getByRole('link', { name: 'Pular para o conteúdo' })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.locator('#conteudo')).toBeFocused();
    expect(errors).toEqual([]);
    await page.screenshot({ path: info.outputPath(`${name}.png`), fullPage: true });
    await context.close();
  });
}

test('painel funciona sem JavaScript e o atalho recebe foco', async ({ browser }, info) => {
  const context = await browser.newContext({ ...info.project.use, javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto('/');
  await expect(page.getByRole('article').filter({ hasText: 'sentinela-old-01' })).toContainText('medição antiga');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Pular para o conteúdo' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#conteudo')).toBeFocused();
  await context.close();
});
