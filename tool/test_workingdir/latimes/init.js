const navigationPromise = page.waitForNavigation()

await page.goto('https://www.latimes.com/')

await page.setViewport({ width: 1274, height: 860 })

await navigationPromise

await page.waitForSelector('.list-items-item:nth-child(2) > .promo-medium > .promo-wrapper > .promo-content > .promo-title-container > .promo-title > .link')
await page.click('.list-items-item:nth-child(2) > .promo-medium > .promo-wrapper > .promo-content > .promo-title-container > .promo-title > .link')

await navigationPromise

await navigationPromise