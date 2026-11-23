# Deploy handEwork on Vercel

Use the Git checkout at `C:\phill\ALLMORROW\handEwork\handework-github`. The sibling `handEwork` folder contains the earlier local setup and its local data. The web app runs on Vercel and uses the separately hosted Flask API.

1. Deploy the Flask API using [the Render configuration](render.yaml) or an equivalent host. Set up the database and apply the migrations. Confirm that `https://YOUR-API-HOST/v1/health` responds.
2. Push the reviewed checkout changes to `allmorrowholdings-cloud/handework`. In Vercel, choose **Add New → Project**, then import that repository. Select **Next.js**, leave **Root Directory** at the repository root and **Output Directory** at its default. The included `vercel.json` uses `npm run build:vercel`. Choose Node.js 22.x.
3. Set `NEXT_PUBLIC_API_URL` in Vercel to the API's HTTPS origin without a trailing slash. Optionally set `NEXT_PUBLIC_MAPBOX_TOKEN` to a public Mapbox token. Configure `WEB_ORIGINS` on the Flask host with the exact frontend origin, such as `https://YOUR-PROJECT.vercel.app`. Add any fixed preview origin you plan to use. Backend secrets belong on the Flask host.
4. Deploy and smoke-test sign-in, marketplace search, and a test booking. If you intend to enable media uploads, configure the backend object storage and verify that an uploaded file loads in the browser.

For a local production check, run `npm ci`, then `npm run build:vercel` from the Git checkout.

## Install from the browser

Open the HTTPS deployment. In Chrome or Edge on desktop, use the install icon in the address bar or the browser menu. On Android Chrome, open the menu and choose **Install app** or **Add to Home screen**. On iPhone or iPad Safari, use **Share → Add to Home Screen** and enable **Open as Web App** if offered. Live app features still need a connection to the API.

## Add an animation to a homepage card manually

1. Export a compact animated WebP or GIF. Use a lowercase filename such as `plumbing-animated.webp`.
2. Put it in `public/services/` in the Git checkout.
3. In `app/page.tsx`, change the Plumbing entry to `image: "/services/plumbing-animated.webp"`. The URL omits the `public` directory. Match the filename case exactly.
4. Open the direct asset URL on your local server, then check the homepage. Commit the asset and the page edit together and push to deploy.

In-app uploads use the Flask API. It accepts JPEG, PNG, WebP, MP4 and PDF, depending on the form, and rejects `image/gif`. For portfolio photos, export a JPEG, PNG or WebP. The API defaults to a 15 MiB limit for the entire upload request, so leave some room below that limit.
