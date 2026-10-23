# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: auth-journey.spec.ts >> owned unsaved route input survives authenticated Legal but never syncs to a clean browser and clears after logout ACK
- Location: ../../../../source/frontend/e2e/auth-journey.spec.ts:657:1

# Error details

```
Test timeout of 120000ms exceeded.
```

# Page snapshot

```yaml
- main [ref=f2e3]:
  - generic [ref=f2e4]:
    - generic [ref=f2e5]:
      - img "A small Unimatch robot overlooks a university and a mountain lake" [ref=f2e6]
      - generic [ref=f2e7]:
        - generic [ref=f2e8]: SAME STUDENTS. BIGGER HORIZONS.
        - heading [level=1] [ref=f2e9]:
          - text: Global opportunitiesstart with
          - emphasis [ref=f2e10]: you.
        - paragraph [ref=f2e11]: Personalized research. Real information. A clearer path.
    - generic [ref=f2e12]:
      - generic [ref=f2e13]:
        - link "Unimatch" [ref=f2e14] [cursor=pointer]:
          - /url: "#/welcome"
        - tablist "Account" [ref=f2e15]:
          - tab "Sign in" [selected] [ref=f2e16] [cursor=pointer]
          - tab "Create account" [ref=f2e17] [cursor=pointer]
        - heading "Welcome back." [level=1] [ref=f2e18]
        - paragraph [ref=f2e19]: Applicant records belong to your workspace. University searches can use your degree, subject and intake preferences. Your name, contacts, grades and budget are excluded from those search queries.
      - generic [ref=f2e20]:
        - generic [ref=f2e21]: Email
        - textbox "Email" [ref=f2e22]
      - generic [ref=f2e23]:
        - generic [ref=f2e24]: Password
        - textbox "Password" [ref=f2e25]
      - button "Sign in" [ref=f2e26] [cursor=pointer]
      - button "I forgot my password" [disabled] [ref=f2e27]
      - button "Create a new workspace" [ref=f2e28] [cursor=pointer]
      - link "Privacy & terms · Drafts awaiting legal review" [ref=f2e29] [cursor=pointer]:
        - /url: "#/legal"
```