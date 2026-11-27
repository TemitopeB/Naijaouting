# Reading promoters' Instagram posts

`fetch_promoters.py` collects recent posts from the accounts in `promoters.txt` and makes a zip
for the site's **Review → Import events**. Claude reads each flyer and caption there, and
nothing goes live until you press **Publish**.

## Once: get a token (Instagram's official API)

You need your own Instagram **Business or Creator** account, linked to a Facebook Page.

1. Go to developers.facebook.com, open (or create) your app, and open **Graph API Explorer**.
2. Pick your app, choose **Get User Access Token**, and tick `instagram_basic`,
   `pages_show_list`, `pages_read_engagement` and `business_management`. Approve it.
3. In the Explorer, run `me/accounts?fields=instagram_business_account` and copy the
   `instagram_business_account` id: that's your `ig_user_id`.
4. Turn the token into a long-lived one (about 60 days): **Access Token Debugger → Extend Access Token**.
5. Copy `config.example.json` to `config.json` and paste both values in.

`config.json` stays on your computer (it's in .gitignore). Never paste the token in a chat or a file you share.
Meta moves these screens around from time to time; the names above are what to look for.

## Every week

```
pip install requests        # first time only
python fetch_promoters.py
```

Then on the site: **Review → Import events → choose `out/posts_<date>.zip`**.

- Only Business and Creator accounts can be read. Personal accounts are listed at the end so
  you can check them by hand.
- Add or remove accounts in `promoters.txt`. Any line with an @handle counts.
- Posts already collected are remembered in `seen.json`, so each zip only has new posts.
- The token lasts about 60 days. When it runs out, the script says so: extend it again (step 4).
- Instagram allows only so many reads an hour. The script watches how much is used and slows down
  (or rests 15 minutes) before it gets blocked; if it is blocked anyway, it waits and tries the same
  account again instead of skipping it. A full run of ~170 accounts can take about an hour.
- Press Ctrl+C to stop early: the posts collected so far are still saved to the zip.
