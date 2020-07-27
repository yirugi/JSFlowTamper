const navigationPromise = page.waitForNavigation()

await page.goto('https://www.cbs.com/shows/tough-as-nails/video/lXcgRhg2_KXJBqsIYU6g2pO7d0Uw6sbl/tough-as-nails-redefining-toughness-get-the-job-done/')

await navigationPromise

await page.waitForSelector('div.start-panel-click-overlay')
await page.click('div.start-panel-click-overlay')

await navigationPromise

await navigationPromise