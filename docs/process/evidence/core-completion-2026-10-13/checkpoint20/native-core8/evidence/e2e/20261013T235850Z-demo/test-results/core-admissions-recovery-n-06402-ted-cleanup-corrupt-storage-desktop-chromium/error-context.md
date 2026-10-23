# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: core-admissions-recovery.spec.ts >> native recovery: lost ACK replay, CAS, physical64 cap, selected cleanup, corrupt storage
- Location: ../../../../../../2026-10-12/g3-execution/source/frontend/e2e/core-admissions-recovery.spec.ts:16:1

# Error details

```
TimeoutError: locator.check: Timeout 20000ms exceeded.
Call log:
  - waiting for getByTestId('admissions-recovery').getByRole('checkbox').first()
    - locator resolved to <input disabled type="checkbox" aria-label="Select local confirmation: Synthetic cap task 8"/>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is not enabled
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is not enabled
    - retrying click action
      - waiting 100ms
    38 × waiting for element to be visible, enabled and stable
       - element is not enabled
     - retrying click action
       - waiting 500ms

```

# Page snapshot

```yaml
- generic [ref=f1e3]:
  - complementary [ref=f1e4]:
    - generic [ref=f1e5]: Unimatch
    - navigation "Main navigation" [ref=f1e7]:
      - button "Home" [ref=f1e8] [cursor=pointer]
      - button "Find" [ref=f1e12] [cursor=pointer]
      - button "Plan" [ref=f1e16] [cursor=pointer]
      - button "Documents" [ref=f1e20] [cursor=pointer]
      - button "Community" [ref=f1e24] [cursor=pointer]
    - navigation "Optional tools" [ref=f1e28]:
      - paragraph [ref=f1e29]: Optional tools
      - button "Exam preparation" [ref=f1e30] [cursor=pointer]
    - generic [ref=f1e34]:
      - paragraph [ref=f1e35]:
        - text: Same students.
        - strong [ref=f1e36]: Bigger horizons.
      - group [ref=f1e37]:
        - generic "Preferences" [ref=f1e38] [cursor=pointer]
        - option "Match system"
        - option "Light" [selected]
        - option "Dark"
        - option "English" [selected]
        - option "Русский"
        - option "Қазақша"
  - generic [ref=f1e39]:
    - banner [ref=f1e40]:
      - generic [ref=f1e41]: Demo data
      - group [ref=f1e42]:
        - generic "Explore⌄" [ref=f1e43] [cursor=pointer]
      - generic [ref=f1e44]:
        - text: Applicant
        - combobox "Applicant" [ref=f1e45]:
          - option "New applicant"
          - option "Demo Applicant (synthetic) · 0 runs" [selected]
      - button "New case" [ref=f1e46] [cursor=pointer]
      - button "Settings" [ref=f1e47] [cursor=pointer]
      - button "Sign out" [ref=f1e48] [cursor=pointer]
    - main "Documents & deadlines" [ref=f1e49]:
      - generic [ref=f1e50]:
        - paragraph [ref=f1e51]: Documents & deadlines
        - heading "Prepare with confidence." [level=1] [ref=f1e52]
        - paragraph [ref=f1e53]: Ordered by lead time, not by deadline. The items at the top depend on other people, so they are the ones that need starting first.
      - generic [ref=f1e54]:
        - generic [ref=f1e55]:
          - generic [ref=f1e56]:
            - heading "Your saved document tasks" [level=2] [ref=f1e58]
            - generic [ref=f1e59]:
              - paragraph [ref=f1e60]: Personal tasks are saved on the server and work without a research result or an exam course.
              - note [ref=f1e61]: Saving has not been confirmed. Keep the original request in recovery; do not create a duplicate.
              - button "Add a document task" [disabled] [ref=f1e62]
              - article [ref=f1e63]:
                - heading "Synthetic other window confirmed" [level=3] [ref=f1e64]
                - generic [ref=f1e65]: You · Not started
                - generic [ref=f1e66]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e67]:
                  - button "Edit document details" [disabled] [ref=f1e68]
                  - button "Update personal status" [disabled] [ref=f1e69]
                  - button "Remove personal record" [disabled] [ref=f1e70]
                  - button "History" [ref=f1e71] [cursor=pointer]
              - article [ref=f1e72]:
                - heading "Synthetic cap task 0" [level=3] [ref=f1e73]
                - generic [ref=f1e74]: You · Not started
                - generic [ref=f1e75]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e76]:
                  - button "Edit document details" [disabled] [ref=f1e77]
                  - button "Update personal status" [disabled] [ref=f1e78]
                  - button "Remove personal record" [disabled] [ref=f1e79]
                  - button "History" [ref=f1e80] [cursor=pointer]
              - article [ref=f1e81]:
                - heading "Synthetic cap task 1" [level=3] [ref=f1e82]
                - generic [ref=f1e83]: You · Not started
                - generic [ref=f1e84]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e85]:
                  - button "Edit document details" [disabled] [ref=f1e86]
                  - button "Update personal status" [disabled] [ref=f1e87]
                  - button "Remove personal record" [disabled] [ref=f1e88]
                  - button "History" [ref=f1e89] [cursor=pointer]
              - article [ref=f1e90]:
                - heading "Synthetic cap task 2" [level=3] [ref=f1e91]
                - generic [ref=f1e92]: You · Not started
                - generic [ref=f1e93]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e94]:
                  - button "Edit document details" [disabled] [ref=f1e95]
                  - button "Update personal status" [disabled] [ref=f1e96]
                  - button "Remove personal record" [disabled] [ref=f1e97]
                  - button "History" [ref=f1e98] [cursor=pointer]
              - article [ref=f1e99]:
                - heading "Synthetic cap task 3" [level=3] [ref=f1e100]
                - generic [ref=f1e101]: You · Not started
                - generic [ref=f1e102]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e103]:
                  - button "Edit document details" [disabled] [ref=f1e104]
                  - button "Update personal status" [disabled] [ref=f1e105]
                  - button "Remove personal record" [disabled] [ref=f1e106]
                  - button "History" [ref=f1e107] [cursor=pointer]
              - article [ref=f1e108]:
                - heading "Synthetic cap task 4" [level=3] [ref=f1e109]
                - generic [ref=f1e110]: You · Not started
                - generic [ref=f1e111]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e112]:
                  - button "Edit document details" [disabled] [ref=f1e113]
                  - button "Update personal status" [disabled] [ref=f1e114]
                  - button "Remove personal record" [disabled] [ref=f1e115]
                  - button "History" [ref=f1e116] [cursor=pointer]
              - article [ref=f1e117]:
                - heading "Synthetic cap task 5" [level=3] [ref=f1e118]
                - generic [ref=f1e119]: You · Not started
                - generic [ref=f1e120]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e121]:
                  - button "Edit document details" [disabled] [ref=f1e122]
                  - button "Update personal status" [disabled] [ref=f1e123]
                  - button "Remove personal record" [disabled] [ref=f1e124]
                  - button "History" [ref=f1e125] [cursor=pointer]
              - article [ref=f1e126]:
                - heading "Synthetic cap task 6" [level=3] [ref=f1e127]
                - generic [ref=f1e128]: You · Not started
                - generic [ref=f1e129]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e130]:
                  - button "Edit document details" [disabled] [ref=f1e131]
                  - button "Update personal status" [disabled] [ref=f1e132]
                  - button "Remove personal record" [disabled] [ref=f1e133]
                  - button "History" [ref=f1e134] [cursor=pointer]
              - article [ref=f1e135]:
                - heading "Synthetic cap task 7" [level=3] [ref=f1e136]
                - generic [ref=f1e137]: You · Not started
                - generic [ref=f1e138]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e139]:
                  - button "Edit document details" [disabled] [ref=f1e140]
                  - button "Update personal status" [disabled] [ref=f1e141]
                  - button "Remove personal record" [disabled] [ref=f1e142]
                  - button "History" [ref=f1e143] [cursor=pointer]
              - article [ref=f1e144]:
                - heading "Synthetic cap task 8" [level=3] [ref=f1e145]
                - generic [ref=f1e146]: You · Not started
                - generic [ref=f1e147]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e148]:
                  - button "Edit document details" [disabled] [ref=f1e149]
                  - button "Update personal status" [disabled] [ref=f1e150]
                  - button "Remove personal record" [disabled] [ref=f1e151]
                  - button "History" [ref=f1e152] [cursor=pointer]
              - article [ref=f1e153]:
                - heading "Synthetic cap task 9" [level=3] [ref=f1e154]
                - generic [ref=f1e155]: You · Not started
                - generic [ref=f1e156]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e157]:
                  - button "Edit document details" [disabled] [ref=f1e158]
                  - button "Update personal status" [disabled] [ref=f1e159]
                  - button "Remove personal record" [disabled] [ref=f1e160]
                  - button "History" [ref=f1e161] [cursor=pointer]
              - article [ref=f1e162]:
                - heading "Synthetic cap task 10" [level=3] [ref=f1e163]
                - generic [ref=f1e164]: You · Not started
                - generic [ref=f1e165]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e166]:
                  - button "Edit document details" [disabled] [ref=f1e167]
                  - button "Update personal status" [disabled] [ref=f1e168]
                  - button "Remove personal record" [disabled] [ref=f1e169]
                  - button "History" [ref=f1e170] [cursor=pointer]
              - article [ref=f1e171]:
                - heading "Synthetic cap task 11" [level=3] [ref=f1e172]
                - generic [ref=f1e173]: You · Not started
                - generic [ref=f1e174]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e175]:
                  - button "Edit document details" [disabled] [ref=f1e176]
                  - button "Update personal status" [disabled] [ref=f1e177]
                  - button "Remove personal record" [disabled] [ref=f1e178]
                  - button "History" [ref=f1e179] [cursor=pointer]
              - article [ref=f1e180]:
                - heading "Synthetic cap task 12" [level=3] [ref=f1e181]
                - generic [ref=f1e182]: You · Not started
                - generic [ref=f1e183]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e184]:
                  - button "Edit document details" [disabled] [ref=f1e185]
                  - button "Update personal status" [disabled] [ref=f1e186]
                  - button "Remove personal record" [disabled] [ref=f1e187]
                  - button "History" [ref=f1e188] [cursor=pointer]
              - article [ref=f1e189]:
                - heading "Synthetic cap task 13" [level=3] [ref=f1e190]
                - generic [ref=f1e191]: You · Not started
                - generic [ref=f1e192]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e193]:
                  - button "Edit document details" [disabled] [ref=f1e194]
                  - button "Update personal status" [disabled] [ref=f1e195]
                  - button "Remove personal record" [disabled] [ref=f1e196]
                  - button "History" [ref=f1e197] [cursor=pointer]
              - article [ref=f1e198]:
                - heading "Synthetic cap task 14" [level=3] [ref=f1e199]
                - generic [ref=f1e200]: You · Not started
                - generic [ref=f1e201]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e202]:
                  - button "Edit document details" [disabled] [ref=f1e203]
                  - button "Update personal status" [disabled] [ref=f1e204]
                  - button "Remove personal record" [disabled] [ref=f1e205]
                  - button "History" [ref=f1e206] [cursor=pointer]
              - article [ref=f1e207]:
                - heading "Synthetic cap task 15" [level=3] [ref=f1e208]
                - generic [ref=f1e209]: You · Not started
                - generic [ref=f1e210]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e211]:
                  - button "Edit document details" [disabled] [ref=f1e212]
                  - button "Update personal status" [disabled] [ref=f1e213]
                  - button "Remove personal record" [disabled] [ref=f1e214]
                  - button "History" [ref=f1e215] [cursor=pointer]
              - article [ref=f1e216]:
                - heading "Synthetic cap task 16" [level=3] [ref=f1e217]
                - generic [ref=f1e218]: You · Not started
                - generic [ref=f1e219]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e220]:
                  - button "Edit document details" [disabled] [ref=f1e221]
                  - button "Update personal status" [disabled] [ref=f1e222]
                  - button "Remove personal record" [disabled] [ref=f1e223]
                  - button "History" [ref=f1e224] [cursor=pointer]
              - article [ref=f1e225]:
                - heading "Synthetic cap task 17" [level=3] [ref=f1e226]
                - generic [ref=f1e227]: You · Not started
                - generic [ref=f1e228]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e229]:
                  - button "Edit document details" [disabled] [ref=f1e230]
                  - button "Update personal status" [disabled] [ref=f1e231]
                  - button "Remove personal record" [disabled] [ref=f1e232]
                  - button "History" [ref=f1e233] [cursor=pointer]
              - article [ref=f1e234]:
                - heading "Synthetic cap task 18" [level=3] [ref=f1e235]
                - generic [ref=f1e236]: You · Not started
                - generic [ref=f1e237]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e238]:
                  - button "Edit document details" [disabled] [ref=f1e239]
                  - button "Update personal status" [disabled] [ref=f1e240]
                  - button "Remove personal record" [disabled] [ref=f1e241]
                  - button "History" [ref=f1e242] [cursor=pointer]
              - article [ref=f1e243]:
                - heading "Synthetic cap task 19" [level=3] [ref=f1e244]
                - generic [ref=f1e245]: You · Not started
                - generic [ref=f1e246]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e247]:
                  - button "Edit document details" [disabled] [ref=f1e248]
                  - button "Update personal status" [disabled] [ref=f1e249]
                  - button "Remove personal record" [disabled] [ref=f1e250]
                  - button "History" [ref=f1e251] [cursor=pointer]
              - article [ref=f1e252]:
                - heading "Synthetic cap task 20" [level=3] [ref=f1e253]
                - generic [ref=f1e254]: You · Not started
                - generic [ref=f1e255]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e256]:
                  - button "Edit document details" [disabled] [ref=f1e257]
                  - button "Update personal status" [disabled] [ref=f1e258]
                  - button "Remove personal record" [disabled] [ref=f1e259]
                  - button "History" [ref=f1e260] [cursor=pointer]
              - article [ref=f1e261]:
                - heading "Synthetic cap task 21" [level=3] [ref=f1e262]
                - generic [ref=f1e263]: You · Not started
                - generic [ref=f1e264]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e265]:
                  - button "Edit document details" [disabled] [ref=f1e266]
                  - button "Update personal status" [disabled] [ref=f1e267]
                  - button "Remove personal record" [disabled] [ref=f1e268]
                  - button "History" [ref=f1e269] [cursor=pointer]
              - article [ref=f1e270]:
                - heading "Synthetic cap task 22" [level=3] [ref=f1e271]
                - generic [ref=f1e272]: You · Not started
                - generic [ref=f1e273]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e274]:
                  - button "Edit document details" [disabled] [ref=f1e275]
                  - button "Update personal status" [disabled] [ref=f1e276]
                  - button "Remove personal record" [disabled] [ref=f1e277]
                  - button "History" [ref=f1e278] [cursor=pointer]
              - article [ref=f1e279]:
                - heading "Synthetic cap task 23" [level=3] [ref=f1e280]
                - generic [ref=f1e281]: You · Not started
                - generic [ref=f1e282]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e283]:
                  - button "Edit document details" [disabled] [ref=f1e284]
                  - button "Update personal status" [disabled] [ref=f1e285]
                  - button "Remove personal record" [disabled] [ref=f1e286]
                  - button "History" [ref=f1e287] [cursor=pointer]
              - article [ref=f1e288]:
                - heading "Synthetic cap task 24" [level=3] [ref=f1e289]
                - generic [ref=f1e290]: You · Not started
                - generic [ref=f1e291]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e292]:
                  - button "Edit document details" [disabled] [ref=f1e293]
                  - button "Update personal status" [disabled] [ref=f1e294]
                  - button "Remove personal record" [disabled] [ref=f1e295]
                  - button "History" [ref=f1e296] [cursor=pointer]
              - article [ref=f1e297]:
                - heading "Synthetic cap task 25" [level=3] [ref=f1e298]
                - generic [ref=f1e299]: You · Not started
                - generic [ref=f1e300]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e301]:
                  - button "Edit document details" [disabled] [ref=f1e302]
                  - button "Update personal status" [disabled] [ref=f1e303]
                  - button "Remove personal record" [disabled] [ref=f1e304]
                  - button "History" [ref=f1e305] [cursor=pointer]
              - article [ref=f1e306]:
                - heading "Synthetic cap task 26" [level=3] [ref=f1e307]
                - generic [ref=f1e308]: You · Not started
                - generic [ref=f1e309]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e310]:
                  - button "Edit document details" [disabled] [ref=f1e311]
                  - button "Update personal status" [disabled] [ref=f1e312]
                  - button "Remove personal record" [disabled] [ref=f1e313]
                  - button "History" [ref=f1e314] [cursor=pointer]
              - article [ref=f1e315]:
                - heading "Synthetic cap task 27" [level=3] [ref=f1e316]
                - generic [ref=f1e317]: You · Not started
                - generic [ref=f1e318]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e319]:
                  - button "Edit document details" [disabled] [ref=f1e320]
                  - button "Update personal status" [disabled] [ref=f1e321]
                  - button "Remove personal record" [disabled] [ref=f1e322]
                  - button "History" [ref=f1e323] [cursor=pointer]
              - article [ref=f1e324]:
                - heading "Synthetic cap task 28" [level=3] [ref=f1e325]
                - generic [ref=f1e326]: You · Not started
                - generic [ref=f1e327]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e328]:
                  - button "Edit document details" [disabled] [ref=f1e329]
                  - button "Update personal status" [disabled] [ref=f1e330]
                  - button "Remove personal record" [disabled] [ref=f1e331]
                  - button "History" [ref=f1e332] [cursor=pointer]
              - article [ref=f1e333]:
                - heading "Synthetic cap task 29" [level=3] [ref=f1e334]
                - generic [ref=f1e335]: You · Not started
                - generic [ref=f1e336]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e337]:
                  - button "Edit document details" [disabled] [ref=f1e338]
                  - button "Update personal status" [disabled] [ref=f1e339]
                  - button "Remove personal record" [disabled] [ref=f1e340]
                  - button "History" [ref=f1e341] [cursor=pointer]
              - article [ref=f1e342]:
                - heading "Synthetic cap task 30" [level=3] [ref=f1e343]
                - generic [ref=f1e344]: You · Not started
                - generic [ref=f1e345]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e346]:
                  - button "Edit document details" [disabled] [ref=f1e347]
                  - button "Update personal status" [disabled] [ref=f1e348]
                  - button "Remove personal record" [disabled] [ref=f1e349]
                  - button "History" [ref=f1e350] [cursor=pointer]
              - article [ref=f1e351]:
                - heading "Synthetic cap task 31" [level=3] [ref=f1e352]
                - generic [ref=f1e353]: You · Not started
                - generic [ref=f1e354]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e355]:
                  - button "Edit document details" [disabled] [ref=f1e356]
                  - button "Update personal status" [disabled] [ref=f1e357]
                  - button "Remove personal record" [disabled] [ref=f1e358]
                  - button "History" [ref=f1e359] [cursor=pointer]
              - article [ref=f1e360]:
                - heading "Synthetic cap task 32" [level=3] [ref=f1e361]
                - generic [ref=f1e362]: You · Not started
                - generic [ref=f1e363]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e364]:
                  - button "Edit document details" [disabled] [ref=f1e365]
                  - button "Update personal status" [disabled] [ref=f1e366]
                  - button "Remove personal record" [disabled] [ref=f1e367]
                  - button "History" [ref=f1e368] [cursor=pointer]
              - article [ref=f1e369]:
                - heading "Synthetic cap task 33" [level=3] [ref=f1e370]
                - generic [ref=f1e371]: You · Not started
                - generic [ref=f1e372]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e373]:
                  - button "Edit document details" [disabled] [ref=f1e374]
                  - button "Update personal status" [disabled] [ref=f1e375]
                  - button "Remove personal record" [disabled] [ref=f1e376]
                  - button "History" [ref=f1e377] [cursor=pointer]
              - article [ref=f1e378]:
                - heading "Synthetic cap task 34" [level=3] [ref=f1e379]
                - generic [ref=f1e380]: You · Not started
                - generic [ref=f1e381]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e382]:
                  - button "Edit document details" [disabled] [ref=f1e383]
                  - button "Update personal status" [disabled] [ref=f1e384]
                  - button "Remove personal record" [disabled] [ref=f1e385]
                  - button "History" [ref=f1e386] [cursor=pointer]
              - article [ref=f1e387]:
                - heading "Synthetic cap task 35" [level=3] [ref=f1e388]
                - generic [ref=f1e389]: You · Not started
                - generic [ref=f1e390]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e391]:
                  - button "Edit document details" [disabled] [ref=f1e392]
                  - button "Update personal status" [disabled] [ref=f1e393]
                  - button "Remove personal record" [disabled] [ref=f1e394]
                  - button "History" [ref=f1e395] [cursor=pointer]
              - article [ref=f1e396]:
                - heading "Synthetic cap task 36" [level=3] [ref=f1e397]
                - generic [ref=f1e398]: You · Not started
                - generic [ref=f1e399]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e400]:
                  - button "Edit document details" [disabled] [ref=f1e401]
                  - button "Update personal status" [disabled] [ref=f1e402]
                  - button "Remove personal record" [disabled] [ref=f1e403]
                  - button "History" [ref=f1e404] [cursor=pointer]
              - article [ref=f1e405]:
                - heading "Synthetic cap task 37" [level=3] [ref=f1e406]
                - generic [ref=f1e407]: You · Not started
                - generic [ref=f1e408]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e409]:
                  - button "Edit document details" [disabled] [ref=f1e410]
                  - button "Update personal status" [disabled] [ref=f1e411]
                  - button "Remove personal record" [disabled] [ref=f1e412]
                  - button "History" [ref=f1e413] [cursor=pointer]
              - article [ref=f1e414]:
                - heading "Synthetic cap task 38" [level=3] [ref=f1e415]
                - generic [ref=f1e416]: You · Not started
                - generic [ref=f1e417]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e418]:
                  - button "Edit document details" [disabled] [ref=f1e419]
                  - button "Update personal status" [disabled] [ref=f1e420]
                  - button "Remove personal record" [disabled] [ref=f1e421]
                  - button "History" [ref=f1e422] [cursor=pointer]
              - article [ref=f1e423]:
                - heading "Synthetic cap task 39" [level=3] [ref=f1e424]
                - generic [ref=f1e425]: You · Not started
                - generic [ref=f1e426]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e427]:
                  - button "Edit document details" [disabled] [ref=f1e428]
                  - button "Update personal status" [disabled] [ref=f1e429]
                  - button "Remove personal record" [disabled] [ref=f1e430]
                  - button "History" [ref=f1e431] [cursor=pointer]
              - article [ref=f1e432]:
                - heading "Synthetic cap task 40" [level=3] [ref=f1e433]
                - generic [ref=f1e434]: You · Not started
                - generic [ref=f1e435]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e436]:
                  - button "Edit document details" [disabled] [ref=f1e437]
                  - button "Update personal status" [disabled] [ref=f1e438]
                  - button "Remove personal record" [disabled] [ref=f1e439]
                  - button "History" [ref=f1e440] [cursor=pointer]
              - article [ref=f1e441]:
                - heading "Synthetic cap task 41" [level=3] [ref=f1e442]
                - generic [ref=f1e443]: You · Not started
                - generic [ref=f1e444]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e445]:
                  - button "Edit document details" [disabled] [ref=f1e446]
                  - button "Update personal status" [disabled] [ref=f1e447]
                  - button "Remove personal record" [disabled] [ref=f1e448]
                  - button "History" [ref=f1e449] [cursor=pointer]
              - article [ref=f1e450]:
                - heading "Synthetic cap task 42" [level=3] [ref=f1e451]
                - generic [ref=f1e452]: You · Not started
                - generic [ref=f1e453]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e454]:
                  - button "Edit document details" [disabled] [ref=f1e455]
                  - button "Update personal status" [disabled] [ref=f1e456]
                  - button "Remove personal record" [disabled] [ref=f1e457]
                  - button "History" [ref=f1e458] [cursor=pointer]
              - article [ref=f1e459]:
                - heading "Synthetic cap task 43" [level=3] [ref=f1e460]
                - generic [ref=f1e461]: You · Not started
                - generic [ref=f1e462]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e463]:
                  - button "Edit document details" [disabled] [ref=f1e464]
                  - button "Update personal status" [disabled] [ref=f1e465]
                  - button "Remove personal record" [disabled] [ref=f1e466]
                  - button "History" [ref=f1e467] [cursor=pointer]
              - article [ref=f1e468]:
                - heading "Synthetic cap task 44" [level=3] [ref=f1e469]
                - generic [ref=f1e470]: You · Not started
                - generic [ref=f1e471]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e472]:
                  - button "Edit document details" [disabled] [ref=f1e473]
                  - button "Update personal status" [disabled] [ref=f1e474]
                  - button "Remove personal record" [disabled] [ref=f1e475]
                  - button "History" [ref=f1e476] [cursor=pointer]
              - article [ref=f1e477]:
                - heading "Synthetic cap task 45" [level=3] [ref=f1e478]
                - generic [ref=f1e479]: You · Not started
                - generic [ref=f1e480]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e481]:
                  - button "Edit document details" [disabled] [ref=f1e482]
                  - button "Update personal status" [disabled] [ref=f1e483]
                  - button "Remove personal record" [disabled] [ref=f1e484]
                  - button "History" [ref=f1e485] [cursor=pointer]
              - article [ref=f1e486]:
                - heading "Synthetic cap task 46" [level=3] [ref=f1e487]
                - generic [ref=f1e488]: You · Not started
                - generic [ref=f1e489]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e490]:
                  - button "Edit document details" [disabled] [ref=f1e491]
                  - button "Update personal status" [disabled] [ref=f1e492]
                  - button "Remove personal record" [disabled] [ref=f1e493]
                  - button "History" [ref=f1e494] [cursor=pointer]
              - article [ref=f1e495]:
                - heading "Synthetic cap task 47" [level=3] [ref=f1e496]
                - generic [ref=f1e497]: You · Not started
                - generic [ref=f1e498]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e499]:
                  - button "Edit document details" [disabled] [ref=f1e500]
                  - button "Update personal status" [disabled] [ref=f1e501]
                  - button "Remove personal record" [disabled] [ref=f1e502]
                  - button "History" [ref=f1e503] [cursor=pointer]
              - article [ref=f1e504]:
                - heading "Synthetic cap task 48" [level=3] [ref=f1e505]
                - generic [ref=f1e506]: You · Not started
                - generic [ref=f1e507]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e508]:
                  - button "Edit document details" [disabled] [ref=f1e509]
                  - button "Update personal status" [disabled] [ref=f1e510]
                  - button "Remove personal record" [disabled] [ref=f1e511]
                  - button "History" [ref=f1e512] [cursor=pointer]
              - article [ref=f1e513]:
                - heading "Synthetic cap task 49" [level=3] [ref=f1e514]
                - generic [ref=f1e515]: You · Not started
                - generic [ref=f1e516]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e517]:
                  - button "Edit document details" [disabled] [ref=f1e518]
                  - button "Update personal status" [disabled] [ref=f1e519]
                  - button "Remove personal record" [disabled] [ref=f1e520]
                  - button "History" [ref=f1e521] [cursor=pointer]
              - article [ref=f1e522]:
                - heading "Synthetic cap task 50" [level=3] [ref=f1e523]
                - generic [ref=f1e524]: You · Not started
                - generic [ref=f1e525]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e526]:
                  - button "Edit document details" [disabled] [ref=f1e527]
                  - button "Update personal status" [disabled] [ref=f1e528]
                  - button "Remove personal record" [disabled] [ref=f1e529]
                  - button "History" [ref=f1e530] [cursor=pointer]
              - article [ref=f1e531]:
                - heading "Synthetic cap task 51" [level=3] [ref=f1e532]
                - generic [ref=f1e533]: You · Not started
                - generic [ref=f1e534]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e535]:
                  - button "Edit document details" [disabled] [ref=f1e536]
                  - button "Update personal status" [disabled] [ref=f1e537]
                  - button "Remove personal record" [disabled] [ref=f1e538]
                  - button "History" [ref=f1e539] [cursor=pointer]
              - article [ref=f1e540]:
                - heading "Synthetic cap task 52" [level=3] [ref=f1e541]
                - generic [ref=f1e542]: You · Not started
                - generic [ref=f1e543]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e544]:
                  - button "Edit document details" [disabled] [ref=f1e545]
                  - button "Update personal status" [disabled] [ref=f1e546]
                  - button "Remove personal record" [disabled] [ref=f1e547]
                  - button "History" [ref=f1e548] [cursor=pointer]
              - article [ref=f1e549]:
                - heading "Synthetic cap task 53" [level=3] [ref=f1e550]
                - generic [ref=f1e551]: You · Not started
                - generic [ref=f1e552]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e553]:
                  - button "Edit document details" [disabled] [ref=f1e554]
                  - button "Update personal status" [disabled] [ref=f1e555]
                  - button "Remove personal record" [disabled] [ref=f1e556]
                  - button "History" [ref=f1e557] [cursor=pointer]
              - article [ref=f1e558]:
                - heading "Synthetic cap task 54" [level=3] [ref=f1e559]
                - generic [ref=f1e560]: You · Not started
                - generic [ref=f1e561]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e562]:
                  - button "Edit document details" [disabled] [ref=f1e563]
                  - button "Update personal status" [disabled] [ref=f1e564]
                  - button "Remove personal record" [disabled] [ref=f1e565]
                  - button "History" [ref=f1e566] [cursor=pointer]
              - article [ref=f1e567]:
                - heading "Synthetic cap task 55" [level=3] [ref=f1e568]
                - generic [ref=f1e569]: You · Not started
                - generic [ref=f1e570]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e571]:
                  - button "Edit document details" [disabled] [ref=f1e572]
                  - button "Update personal status" [disabled] [ref=f1e573]
                  - button "Remove personal record" [disabled] [ref=f1e574]
                  - button "History" [ref=f1e575] [cursor=pointer]
              - article [ref=f1e576]:
                - heading "Synthetic cap task 56" [level=3] [ref=f1e577]
                - generic [ref=f1e578]: You · Not started
                - generic [ref=f1e579]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e580]:
                  - button "Edit document details" [disabled] [ref=f1e581]
                  - button "Update personal status" [disabled] [ref=f1e582]
                  - button "Remove personal record" [disabled] [ref=f1e583]
                  - button "History" [ref=f1e584] [cursor=pointer]
              - article [ref=f1e585]:
                - heading "Synthetic cap task 57" [level=3] [ref=f1e586]
                - generic [ref=f1e587]: You · Not started
                - generic [ref=f1e588]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e589]:
                  - button "Edit document details" [disabled] [ref=f1e590]
                  - button "Update personal status" [disabled] [ref=f1e591]
                  - button "Remove personal record" [disabled] [ref=f1e592]
                  - button "History" [ref=f1e593] [cursor=pointer]
              - article [ref=f1e594]:
                - heading "Synthetic cap task 58" [level=3] [ref=f1e595]
                - generic [ref=f1e596]: You · Not started
                - generic [ref=f1e597]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e598]:
                  - button "Edit document details" [disabled] [ref=f1e599]
                  - button "Update personal status" [disabled] [ref=f1e600]
                  - button "Remove personal record" [disabled] [ref=f1e601]
                  - button "History" [ref=f1e602] [cursor=pointer]
              - article [ref=f1e603]:
                - heading "Synthetic cap task 59" [level=3] [ref=f1e604]
                - generic [ref=f1e605]: You · Not started
                - generic [ref=f1e606]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e607]:
                  - button "Edit document details" [disabled] [ref=f1e608]
                  - button "Update personal status" [disabled] [ref=f1e609]
                  - button "Remove personal record" [disabled] [ref=f1e610]
                  - button "History" [ref=f1e611] [cursor=pointer]
              - article [ref=f1e612]:
                - heading "Synthetic cap task 60" [level=3] [ref=f1e613]
                - generic [ref=f1e614]: You · Not started
                - generic [ref=f1e615]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e616]:
                  - button "Edit document details" [disabled] [ref=f1e617]
                  - button "Update personal status" [disabled] [ref=f1e618]
                  - button "Remove personal record" [disabled] [ref=f1e619]
                  - button "History" [ref=f1e620] [cursor=pointer]
              - article [ref=f1e621]:
                - heading "Synthetic cap task 61" [level=3] [ref=f1e622]
                - generic [ref=f1e623]: You · Not started
                - generic [ref=f1e624]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e625]:
                  - button "Edit document details" [disabled] [ref=f1e626]
                  - button "Update personal status" [disabled] [ref=f1e627]
                  - button "Remove personal record" [disabled] [ref=f1e628]
                  - button "History" [ref=f1e629] [cursor=pointer]
              - article [ref=f1e630]:
                - heading "Synthetic cap task 62" [level=3] [ref=f1e631]
                - generic [ref=f1e632]: You · Not started
                - generic [ref=f1e633]: A personal report is not university verification or proof of an official submission.
                - generic [ref=f1e634]:
                  - button "Edit document details" [disabled] [ref=f1e635]
                  - button "Update personal status" [disabled] [ref=f1e636]
                  - button "Remove personal record" [disabled] [ref=f1e637]
                  - button "History" [ref=f1e638] [cursor=pointer]
          - generic [ref=f1e639]:
            - heading "Link an exact requirement" [level=2] [ref=f1e641]
            - generic [ref=f1e642]:
              - paragraph [ref=f1e643]: Choose one original requirement occurrence from a selected programme. Identical names are not merged.
              - paragraph [ref=f1e644]: No requirement references from this loaded case are available. You can still create a personal task.
              - generic [ref=f1e645]:
                - text: Choose a programme requirement
                - combobox "Choose a programme requirement" [ref=f1e646]:
                  - option "Choose a programme requirement" [selected]
              - generic [ref=f1e647]:
                - text: Task to link
                - combobox "Task to link" [ref=f1e648]:
                  - option "Create a new linked task" [selected]
                  - option "Synthetic other window confirmed"
                  - option "Synthetic cap task 0"
                  - option "Synthetic cap task 1"
                  - option "Synthetic cap task 2"
                  - option "Synthetic cap task 3"
                  - option "Synthetic cap task 4"
                  - option "Synthetic cap task 5"
                  - option "Synthetic cap task 6"
                  - option "Synthetic cap task 7"
                  - option "Synthetic cap task 8"
                  - option "Synthetic cap task 9"
                  - option "Synthetic cap task 10"
                  - option "Synthetic cap task 11"
                  - option "Synthetic cap task 12"
                  - option "Synthetic cap task 13"
                  - option "Synthetic cap task 14"
                  - option "Synthetic cap task 15"
                  - option "Synthetic cap task 16"
                  - option "Synthetic cap task 17"
                  - option "Synthetic cap task 18"
                  - option "Synthetic cap task 19"
                  - option "Synthetic cap task 20"
                  - option "Synthetic cap task 21"
                  - option "Synthetic cap task 22"
                  - option "Synthetic cap task 23"
                  - option "Synthetic cap task 24"
                  - option "Synthetic cap task 25"
                  - option "Synthetic cap task 26"
                  - option "Synthetic cap task 27"
                  - option "Synthetic cap task 28"
                  - option "Synthetic cap task 29"
                  - option "Synthetic cap task 30"
                  - option "Synthetic cap task 31"
                  - option "Synthetic cap task 32"
                  - option "Synthetic cap task 33"
                  - option "Synthetic cap task 34"
                  - option "Synthetic cap task 35"
                  - option "Synthetic cap task 36"
                  - option "Synthetic cap task 37"
                  - option "Synthetic cap task 38"
                  - option "Synthetic cap task 39"
                  - option "Synthetic cap task 40"
                  - option "Synthetic cap task 41"
                  - option "Synthetic cap task 42"
                  - option "Synthetic cap task 43"
                  - option "Synthetic cap task 44"
                  - option "Synthetic cap task 45"
                  - option "Synthetic cap task 46"
                  - option "Synthetic cap task 47"
                  - option "Synthetic cap task 48"
                  - option "Synthetic cap task 49"
                  - option "Synthetic cap task 50"
                  - option "Synthetic cap task 51"
                  - option "Synthetic cap task 52"
                  - option "Synthetic cap task 53"
                  - option "Synthetic cap task 54"
                  - option "Synthetic cap task 55"
                  - option "Synthetic cap task 56"
                  - option "Synthetic cap task 57"
                  - option "Synthetic cap task 58"
                  - option "Synthetic cap task 59"
                  - option "Synthetic cap task 60"
                  - option "Synthetic cap task 61"
                  - option "Synthetic cap task 62"
              - button "Review current requirement" [disabled] [ref=f1e649]
          - generic [ref=f1e650]:
            - heading "Review earlier browser marks" [level=2] [ref=f1e652]
            - generic [ref=f1e653]:
              - paragraph [ref=f1e654]: Only unambiguous marks from this loaded case can be offered. Choose your own unreported task and confirm the mapping. Source version and original reporting time remain unknown.
              - button "Read marks for this case" [ref=f1e655] [cursor=pointer]
          - generic [ref=f1e656]:
            - heading "Save recovery" [level=2] [ref=f1e658]
            - generic [ref=f1e659]:
              - paragraph [ref=f1e660]: If confirmation is lost, keep the original request and retry it explicitly.
              - note [ref=f1e661]: The local journal has 64 entries. A new request needs space; only selected confirmed entries can be cleared.
              - generic [ref=f1e662]:
                - generic [ref=f1e663]:
                  - strong [ref=f1e664]: Synthetic cap task 8
                  - generic [ref=f1e665]: Saving confirmed by the server
                - generic [ref=f1e666]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 8" [disabled] [ref=f1e667]'
                  - text: Select local confirmation
              - generic [ref=f1e668]:
                - generic [ref=f1e669]:
                  - strong [ref=f1e670]: Synthetic cap task 59
                  - generic [ref=f1e671]: Saving confirmed by the server
                - generic [ref=f1e672]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 59" [disabled] [ref=f1e673]'
                  - text: Select local confirmation
              - generic [ref=f1e674]:
                - generic [ref=f1e675]:
                  - strong [ref=f1e676]: Synthetic cap task 15
                  - generic [ref=f1e677]: Saving confirmed by the server
                - generic [ref=f1e678]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 15" [disabled] [ref=f1e679]'
                  - text: Select local confirmation
              - generic [ref=f1e680]:
                - generic [ref=f1e681]:
                  - strong [ref=f1e682]: Synthetic cap task 40
                  - generic [ref=f1e683]: Saving confirmed by the server
                - generic [ref=f1e684]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 40" [disabled] [ref=f1e685]'
                  - text: Select local confirmation
              - generic [ref=f1e686]:
                - generic [ref=f1e687]:
                  - strong [ref=f1e688]: Synthetic cap task 18
                  - generic [ref=f1e689]: Saving confirmed by the server
                - generic [ref=f1e690]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 18" [disabled] [ref=f1e691]'
                  - text: Select local confirmation
              - generic [ref=f1e692]:
                - generic [ref=f1e693]:
                  - strong [ref=f1e694]: Synthetic cap task 2
                  - generic [ref=f1e695]: Saving confirmed by the server
                - generic [ref=f1e696]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 2" [disabled] [ref=f1e697]'
                  - text: Select local confirmation
              - generic [ref=f1e698]:
                - generic [ref=f1e699]:
                  - strong [ref=f1e700]: Synthetic cap task 34
                  - generic [ref=f1e701]: Saving confirmed by the server
                - generic [ref=f1e702]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 34" [disabled] [ref=f1e703]'
                  - text: Select local confirmation
              - generic [ref=f1e704]:
                - generic [ref=f1e705]:
                  - strong [ref=f1e706]: Synthetic cap task 60
                  - generic [ref=f1e707]: Saving confirmed by the server
                - generic [ref=f1e708]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 60" [disabled] [ref=f1e709]'
                  - text: Select local confirmation
              - generic [ref=f1e710]:
                - generic [ref=f1e711]:
                  - strong [ref=f1e712]: Synthetic cap task 44
                  - generic [ref=f1e713]: Saving confirmed by the server
                - generic [ref=f1e714]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 44" [disabled] [ref=f1e715]'
                  - text: Select local confirmation
              - generic [ref=f1e716]:
                - generic [ref=f1e717]:
                  - strong [ref=f1e718]: Synthetic cap task 1
                  - generic [ref=f1e719]: Saving confirmed by the server
                - generic [ref=f1e720]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 1" [disabled] [ref=f1e721]'
                  - text: Select local confirmation
              - generic [ref=f1e722]:
                - generic [ref=f1e723]:
                  - strong [ref=f1e724]: Synthetic cap task 21
                  - generic [ref=f1e725]: Saving confirmed by the server
                - generic [ref=f1e726]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 21" [disabled] [ref=f1e727]'
                  - text: Select local confirmation
              - generic [ref=f1e728]:
                - generic [ref=f1e729]:
                  - strong [ref=f1e730]: Synthetic cap task 12
                  - generic [ref=f1e731]: Saving confirmed by the server
                - generic [ref=f1e732]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 12" [disabled] [ref=f1e733]'
                  - text: Select local confirmation
              - generic [ref=f1e734]:
                - generic [ref=f1e735]:
                  - strong [ref=f1e736]: Synthetic cap task 9
                  - generic [ref=f1e737]: Saving confirmed by the server
                - generic [ref=f1e738]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 9" [disabled] [ref=f1e739]'
                  - text: Select local confirmation
              - generic [ref=f1e740]:
                - generic [ref=f1e741]:
                  - strong [ref=f1e742]: Synthetic cap task 57
                  - generic [ref=f1e743]: Saving confirmed by the server
                - generic [ref=f1e744]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 57" [disabled] [ref=f1e745]'
                  - text: Select local confirmation
              - generic [ref=f1e746]:
                - generic [ref=f1e747]:
                  - strong [ref=f1e748]: Synthetic cap task 11
                  - generic [ref=f1e749]: Saving confirmed by the server
                - generic [ref=f1e750]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 11" [disabled] [ref=f1e751]'
                  - text: Select local confirmation
              - generic [ref=f1e752]:
                - generic [ref=f1e753]:
                  - strong [ref=f1e754]: Synthetic cap task 47
                  - generic [ref=f1e755]: Saving confirmed by the server
                - generic [ref=f1e756]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 47" [disabled] [ref=f1e757]'
                  - text: Select local confirmation
              - generic [ref=f1e758]:
                - generic [ref=f1e759]:
                  - strong [ref=f1e760]: Synthetic cap task 39
                  - generic [ref=f1e761]: Saving confirmed by the server
                - generic [ref=f1e762]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 39" [disabled] [ref=f1e763]'
                  - text: Select local confirmation
              - generic [ref=f1e764]:
                - generic [ref=f1e765]:
                  - strong [ref=f1e766]: Synthetic cap task 27
                  - generic [ref=f1e767]: Saving confirmed by the server
                - generic [ref=f1e768]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 27" [disabled] [ref=f1e769]'
                  - text: Select local confirmation
              - generic [ref=f1e770]:
                - generic [ref=f1e771]:
                  - strong [ref=f1e772]: Synthetic cap task 58
                  - generic [ref=f1e773]: Saving confirmed by the server
                - generic [ref=f1e774]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 58" [disabled] [ref=f1e775]'
                  - text: Select local confirmation
              - generic [ref=f1e776]:
                - generic [ref=f1e777]:
                  - strong [ref=f1e778]: Synthetic cap task 52
                  - generic [ref=f1e779]: Saving confirmed by the server
                - generic [ref=f1e780]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 52" [disabled] [ref=f1e781]'
                  - text: Select local confirmation
              - generic [ref=f1e782]:
                - generic [ref=f1e783]:
                  - strong [ref=f1e784]: Synthetic cap task 4
                  - generic [ref=f1e785]: Saving confirmed by the server
                - generic [ref=f1e786]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 4" [disabled] [ref=f1e787]'
                  - text: Select local confirmation
              - generic [ref=f1e788]:
                - generic [ref=f1e789]:
                  - strong [ref=f1e790]: Synthetic cap task 19
                  - generic [ref=f1e791]: Saving confirmed by the server
                - generic [ref=f1e792]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 19" [disabled] [ref=f1e793]'
                  - text: Select local confirmation
              - generic [ref=f1e794]:
                - generic [ref=f1e795]:
                  - strong [ref=f1e796]: Synthetic cap task 31
                  - generic [ref=f1e797]: Saving confirmed by the server
                - generic [ref=f1e798]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 31" [disabled] [ref=f1e799]'
                  - text: Select local confirmation
              - generic [ref=f1e800]:
                - generic [ref=f1e801]:
                  - strong [ref=f1e802]: Synthetic cap task 22
                  - generic [ref=f1e803]: Saving confirmed by the server
                - generic [ref=f1e804]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 22" [disabled] [ref=f1e805]'
                  - text: Select local confirmation
              - generic [ref=f1e806]:
                - generic [ref=f1e807]:
                  - strong [ref=f1e808]: Synthetic cap task 56
                  - generic [ref=f1e809]: Saving confirmed by the server
                - generic [ref=f1e810]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 56" [disabled] [ref=f1e811]'
                  - text: Select local confirmation
              - generic [ref=f1e812]:
                - generic [ref=f1e813]:
                  - strong [ref=f1e814]: Synthetic cap task 46
                  - generic [ref=f1e815]: Saving confirmed by the server
                - generic [ref=f1e816]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 46" [disabled] [ref=f1e817]'
                  - text: Select local confirmation
              - generic [ref=f1e818]:
                - generic [ref=f1e819]:
                  - strong [ref=f1e820]: Synthetic cap task 30
                  - generic [ref=f1e821]: Saving confirmed by the server
                - generic [ref=f1e822]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 30" [disabled] [ref=f1e823]'
                  - text: Select local confirmation
              - generic [ref=f1e824]:
                - generic [ref=f1e825]:
                  - strong [ref=f1e826]: Synthetic cap task 38
                  - generic [ref=f1e827]: Saving confirmed by the server
                - generic [ref=f1e828]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 38" [disabled] [ref=f1e829]'
                  - text: Select local confirmation
              - generic [ref=f1e830]:
                - generic [ref=f1e831]:
                  - strong [ref=f1e832]: Synthetic cap task 48
                  - generic [ref=f1e833]: Saving confirmed by the server
                - generic [ref=f1e834]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 48" [disabled] [ref=f1e835]'
                  - text: Select local confirmation
              - generic [ref=f1e836]:
                - generic [ref=f1e837]:
                  - strong [ref=f1e838]: Synthetic cap task 42
                  - generic [ref=f1e839]: Saving confirmed by the server
                - generic [ref=f1e840]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 42" [disabled] [ref=f1e841]'
                  - text: Select local confirmation
              - generic [ref=f1e842]:
                - generic [ref=f1e843]:
                  - strong [ref=f1e844]: Synthetic cap task 28
                  - generic [ref=f1e845]: Saving confirmed by the server
                - generic [ref=f1e846]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 28" [disabled] [ref=f1e847]'
                  - text: Select local confirmation
              - generic [ref=f1e848]:
                - generic [ref=f1e849]:
                  - strong [ref=f1e850]: Synthetic cap task 32
                  - generic [ref=f1e851]: Saving confirmed by the server
                - generic [ref=f1e852]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 32" [disabled] [ref=f1e853]'
                  - text: Select local confirmation
              - generic [ref=f1e854]:
                - generic [ref=f1e855]:
                  - strong [ref=f1e856]: Synthetic cap task 0
                  - generic [ref=f1e857]: Saving confirmed by the server
                - generic [ref=f1e858]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 0" [disabled] [ref=f1e859]'
                  - text: Select local confirmation
              - generic [ref=f1e860]:
                - generic [ref=f1e861]:
                  - strong [ref=f1e862]: Synthetic cap task 13
                  - generic [ref=f1e863]: Saving confirmed by the server
                - generic [ref=f1e864]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 13" [disabled] [ref=f1e865]'
                  - text: Select local confirmation
              - generic [ref=f1e866]:
                - generic [ref=f1e867]:
                  - strong [ref=f1e868]: Synthetic cap task 33
                  - generic [ref=f1e869]: Saving confirmed by the server
                - generic [ref=f1e870]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 33" [disabled] [ref=f1e871]'
                  - text: Select local confirmation
              - generic [ref=f1e872]:
                - generic [ref=f1e873]:
                  - strong [ref=f1e874]: Synthetic cap task 25
                  - generic [ref=f1e875]: Saving confirmed by the server
                - generic [ref=f1e876]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 25" [disabled] [ref=f1e877]'
                  - text: Select local confirmation
              - generic [ref=f1e878]:
                - generic [ref=f1e879]:
                  - strong [ref=f1e880]: Synthetic cap task 53
                  - generic [ref=f1e881]: Saving confirmed by the server
                - generic [ref=f1e882]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 53" [disabled] [ref=f1e883]'
                  - text: Select local confirmation
              - generic [ref=f1e884]:
                - generic [ref=f1e885]:
                  - strong [ref=f1e886]: Synthetic cap task 43
                  - generic [ref=f1e887]: Saving confirmed by the server
                - generic [ref=f1e888]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 43" [disabled] [ref=f1e889]'
                  - text: Select local confirmation
              - generic [ref=f1e890]:
                - generic [ref=f1e891]:
                  - strong [ref=f1e892]: Synthetic cap task 49
                  - generic [ref=f1e893]: Saving confirmed by the server
                - generic [ref=f1e894]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 49" [disabled] [ref=f1e895]'
                  - text: Select local confirmation
              - generic [ref=f1e896]:
                - generic [ref=f1e897]:
                  - strong [ref=f1e898]: Synthetic cap task 7
                  - generic [ref=f1e899]: Saving confirmed by the server
                - generic [ref=f1e900]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 7" [disabled] [ref=f1e901]'
                  - text: Select local confirmation
              - generic [ref=f1e902]:
                - generic [ref=f1e903]:
                  - strong [ref=f1e904]: Synthetic cap task 23
                  - generic [ref=f1e905]: Saving confirmed by the server
                - generic [ref=f1e906]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 23" [disabled] [ref=f1e907]'
                  - text: Select local confirmation
              - generic [ref=f1e908]:
                - generic [ref=f1e909]:
                  - strong [ref=f1e910]: Synthetic cap task 24
                  - generic [ref=f1e911]: Saving confirmed by the server
                - generic [ref=f1e912]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 24" [disabled] [ref=f1e913]'
                  - text: Select local confirmation
              - generic [ref=f1e914]:
                - generic [ref=f1e915]:
                  - strong [ref=f1e916]: Synthetic cap task 5
                  - generic [ref=f1e917]: Saving confirmed by the server
                - generic [ref=f1e918]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 5" [disabled] [ref=f1e919]'
                  - text: Select local confirmation
              - generic [ref=f1e920]:
                - generic [ref=f1e921]:
                  - strong [ref=f1e922]: Synthetic cap task 14
                  - generic [ref=f1e923]: Saving confirmed by the server
                - generic [ref=f1e924]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 14" [disabled] [ref=f1e925]'
                  - text: Select local confirmation
              - generic [ref=f1e926]:
                - generic [ref=f1e927]:
                  - strong [ref=f1e928]: Synthetic cap task 26
                  - generic [ref=f1e929]: Saving confirmed by the server
                - generic [ref=f1e930]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 26" [disabled] [ref=f1e931]'
                  - text: Select local confirmation
              - generic [ref=f1e932]:
                - generic [ref=f1e933]:
                  - strong [ref=f1e934]: Synthetic cap task 17
                  - generic [ref=f1e935]: Saving confirmed by the server
                - generic [ref=f1e936]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 17" [disabled] [ref=f1e937]'
                  - text: Select local confirmation
              - generic [ref=f1e938]:
                - generic [ref=f1e939]:
                  - strong [ref=f1e940]: Synthetic cap task 16
                  - generic [ref=f1e941]: Saving confirmed by the server
                - generic [ref=f1e942]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 16" [disabled] [ref=f1e943]'
                  - text: Select local confirmation
              - generic [ref=f1e944]:
                - generic [ref=f1e945]:
                  - strong [ref=f1e946]: Synthetic cap task 6
                  - generic [ref=f1e947]: Saving confirmed by the server
                - generic [ref=f1e948]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 6" [disabled] [ref=f1e949]'
                  - text: Select local confirmation
              - generic [ref=f1e950]:
                - generic [ref=f1e951]:
                  - strong [ref=f1e952]: Synthetic cap task 51
                  - generic [ref=f1e953]: Saving confirmed by the server
                - generic [ref=f1e954]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 51" [disabled] [ref=f1e955]'
                  - text: Select local confirmation
              - generic [ref=f1e956]:
                - generic [ref=f1e957]:
                  - strong [ref=f1e958]: Synthetic cap task 55
                  - generic [ref=f1e959]: Saving confirmed by the server
                - generic [ref=f1e960]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 55" [disabled] [ref=f1e961]'
                  - text: Select local confirmation
              - generic [ref=f1e962]:
                - generic [ref=f1e963]:
                  - strong [ref=f1e964]: Synthetic cap task 61
                  - generic [ref=f1e965]: Saving confirmed by the server
                - generic [ref=f1e966]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 61" [disabled] [ref=f1e967]'
                  - text: Select local confirmation
              - generic [ref=f1e968]:
                - generic [ref=f1e969]:
                  - strong [ref=f1e970]: Synthetic cap task 35
                  - generic [ref=f1e971]: Saving confirmed by the server
                - generic [ref=f1e972]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 35" [disabled] [ref=f1e973]'
                  - text: Select local confirmation
              - generic [ref=f1e974]:
                - generic [ref=f1e975]:
                  - strong [ref=f1e976]: Synthetic cap task 45
                  - generic [ref=f1e977]: Saving confirmed by the server
                - generic [ref=f1e978]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 45" [disabled] [ref=f1e979]'
                  - text: Select local confirmation
              - generic [ref=f1e980]:
                - generic [ref=f1e981]:
                  - strong [ref=f1e982]: Synthetic cap task 41
                  - generic [ref=f1e983]: Saving confirmed by the server
                - generic [ref=f1e984]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 41" [disabled] [ref=f1e985]'
                  - text: Select local confirmation
              - generic [ref=f1e986]:
                - generic [ref=f1e987]:
                  - strong [ref=f1e988]: Synthetic cap task 37
                  - generic [ref=f1e989]: Saving confirmed by the server
                - generic [ref=f1e990]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 37" [disabled] [ref=f1e991]'
                  - text: Select local confirmation
              - generic [ref=f1e993]:
                - strong [ref=f1e994]: Synthetic stale window edit
                - generic [ref=f1e995]: Data changed. Review the saved version before creating a new request.
              - generic [ref=f1e996]:
                - generic [ref=f1e997]:
                  - strong [ref=f1e998]: Synthetic cap task 50
                  - generic [ref=f1e999]: Saving confirmed by the server
                - generic [ref=f1e1000]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 50" [disabled] [ref=f1e1001]'
                  - text: Select local confirmation
              - generic [ref=f1e1002]:
                - generic [ref=f1e1003]:
                  - strong [ref=f1e1004]: Synthetic cap task 62
                  - generic [ref=f1e1005]: Saving confirmed by the server
                - generic [ref=f1e1006]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 62" [disabled] [ref=f1e1007]'
                  - text: Select local confirmation
              - generic [ref=f1e1008]:
                - generic [ref=f1e1009]:
                  - strong [ref=f1e1010]: Synthetic cap task 54
                  - generic [ref=f1e1011]: Saving confirmed by the server
                - generic [ref=f1e1012]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 54" [disabled] [ref=f1e1013]'
                  - text: Select local confirmation
              - generic [ref=f1e1014]:
                - generic [ref=f1e1015]:
                  - strong [ref=f1e1016]: Synthetic cap task 20
                  - generic [ref=f1e1017]: Saving confirmed by the server
                - generic [ref=f1e1018]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 20" [disabled] [ref=f1e1019]'
                  - text: Select local confirmation
              - generic [ref=f1e1020]:
                - generic [ref=f1e1021]:
                  - strong [ref=f1e1022]: Synthetic cap task 3
                  - generic [ref=f1e1023]: Saving confirmed by the server
                - generic [ref=f1e1024]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 3" [disabled] [ref=f1e1025]'
                  - text: Select local confirmation
              - generic [ref=f1e1026]:
                - generic [ref=f1e1027]:
                  - strong [ref=f1e1028]: Synthetic cap task 10
                  - generic [ref=f1e1029]: Saving confirmed by the server
                - generic [ref=f1e1030]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 10" [disabled] [ref=f1e1031]'
                  - text: Select local confirmation
              - generic [ref=f1e1032]:
                - generic [ref=f1e1033]:
                  - strong [ref=f1e1034]: Synthetic cap task 36
                  - generic [ref=f1e1035]: Saving confirmed by the server
                - generic [ref=f1e1036]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 36" [disabled] [ref=f1e1037]'
                  - text: Select local confirmation
              - generic [ref=f1e1038]:
                - generic [ref=f1e1039]:
                  - strong [ref=f1e1040]: Synthetic cap task 29
                  - generic [ref=f1e1041]: Saving confirmed by the server
                - generic [ref=f1e1042]:
                  - 'checkbox "Select local confirmation: Synthetic cap task 29" [disabled] [ref=f1e1043]'
                  - text: Select local confirmation
              - note [ref=f1e1044]: The local journal has 64 entries. A new request needs space; only selected confirmed entries can be cleared.
              - generic [ref=f1e1045]:
                - paragraph [ref=f1e1046]: Clearing selected local confirmations does not delete saved records or server history. Unresolved requests are kept.
                - button "Clear selected local confirmations" [disabled] [ref=f1e1047]
              - button "Refresh saved records" [ref=f1e1049] [cursor=pointer]
        - note [ref=f1e1050]: The earlier checklist marks below are browser-only notes. They are not saved server tasks or official readiness; transfer requires your explicit review.
        - generic [ref=f1e1051]:
          - generic [ref=f1e1052]:
            - paragraph [ref=f1e1053]: No checklists yet
            - text: Choose a programme in Find, then collect its official requirements from Plan.
          - button "Choose programmes" [ref=f1e1054] [cursor=pointer]
```

# Test source

```ts
  1   | /** Labelled network faults on real owned native API; no fabricated receipts. */
  2   | import { test, expect, type Page } from '@playwright/test';
  3   | 
  4   | const auth = process.env.CORE_NATIVE_AUTH === 'true';
  5   | const EMAIL = `core-recovery-${Date.now()}-${process.pid}@ashyq.invalid`;
  6   | const PASSWORD = 'synthetic-recovery-passphrase-2026';
  7   | async function login(page: Page) {
  8   |   await page.goto('/#/sign-in'); await page.getByTestId('auth-email').fill(EMAIL);
  9   |   await page.getByTestId('auth-password').fill(PASSWORD); await page.getByTestId('auth-submit').click();
  10  |   await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  11  | }
  12  | async function editor(page: Page, label: string) {
  13  |   await page.getByRole('button', { name: 'Add a document task', exact: true }).click();
  14  |   await page.getByLabel('Task name', { exact: true }).fill(label);
  15  | }
  16  | test('native recovery: lost ACK replay, CAS, physical64 cap, selected cleanup, corrupt storage', async ({ page, browser }, info) => {
  17  |   test.setTimeout(360_000);
  18  |   if (auth) {
  19  |     await page.goto('/#/sign-in'); await page.getByTestId('auth-mode-toggle').click();
  20  |     await page.getByTestId('auth-name').fill('Synthetic Recovery Applicant');
  21  |     await page.getByTestId('auth-organization').fill('Synthetic Recovery Workspace');
  22  |     await page.getByTestId('auth-email').fill(EMAIL); await page.getByTestId('auth-password').fill(PASSWORD);
  23  |     await page.getByTestId('auth-submit').click(); await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  24  |   }
  25  |   await page.goto('/#/profile'); await page.getByTestId('load-demo-profile').click();
  26  |   const replacement = page.getByTestId('confirm-replace'); if (await replacement.isVisible().catch(() => false)) await replacement.click();
  27  |   const saved = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/profiles');
  28  |   await page.getByTestId('save-profile').click(); const savedResponse = await saved; expect(savedResponse.status()).toBe(201);
  29  |   const profile = await savedResponse.json(); const endpoint = `/api/profiles/${profile.id}/admissions-actions`;
  30  |   await page.goto('/#/documents');
  31  |   let originalReceipt: Record<string, unknown> | undefined; let dropped = false; const bodies: string[] = [];
  32  |   page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname === endpoint + '/commands') bodies.push(request.postData()!); });
  33  |   // The server commits and returns its actual receipt. Only UI delivery is lost.
  34  |   await page.route('**' + endpoint + '/commands', async route => {
  35  |     if (dropped || route.request().method() !== 'POST') return route.continue();
  36  |     dropped = true; const response = await route.fetch(); expect(response.status()).toBe(200);
  37  |     originalReceipt = await response.json(); await route.abort('failed');
  38  |   });
  39  |   await editor(page, 'Synthetic lost response task'); await page.getByRole('button', { name: 'Save on server', exact: true }).click();
  40  |   const recovery = page.getByTestId('admissions-recovery');
  41  |   await expect(recovery.getByText('Confirmation has not been received', { exact: true })).toBeVisible();
  42  |   expect(bodies).toHaveLength(1); const write = JSON.parse(bodies[0]);
  43  |   await page.unroute('**' + endpoint + '/commands'); await page.reload();
  44  |   await expect(page.getByRole('heading', { name: 'Synthetic lost response task', exact: true })).toBeVisible();
  45  |   const retried = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === endpoint + '/commands');
  46  |   await recovery.getByRole('button', { name: 'Retry original request', exact: true }).click();
  47  |   const replay = await retried; expect(replay.status()).toBe(200); expect(await replay.json()).toEqual(originalReceipt);
  48  |   expect(bodies).toHaveLength(2); expect(bodies[1]).toBe(bodies[0]);
  49  |   let current = await (await page.request.get(endpoint)).json(); expect(current.revision).toBe(1); expect(current.state.document_tasks).toHaveLength(1);
  50  |   const task = current.state.document_tasks[0];
  51  |   const secondContext = await browser.newContext(); const second = await secondContext.newPage();
  52  |   try {
  53  |     if (auth) await login(second); else await second.goto('/#/home');
  54  |     await second.getByRole('combobox', { name: 'Applicant', exact: true }).selectOption(profile.id);
  55  |     await second.goto('/#/documents');
  56  |     await expect(second.getByRole('heading', { name: task.personal.label, exact: true })).toBeVisible();
  57  |     const card = page.getByTestId('personal-document-task').filter({ has: page.getByRole('heading', { name: task.personal.label, exact: true }) });
  58  |     await card.getByRole('button', { name: 'Edit document details', exact: true }).click();
  59  |     await page.getByLabel('Task name', { exact: true }).fill('Synthetic stale window edit');
  60  |     await page.getByRole('checkbox', { name: 'I confirm these personal details; previous reports and requirement references remain in history.', exact: true }).check();
  61  |     const other = second.getByTestId('personal-document-task').filter({ has: second.getByRole('heading', { name: task.personal.label, exact: true }) });
  62  |     await other.getByRole('button', { name: 'Edit document details', exact: true }).click();
  63  |     await second.getByLabel('Task name', { exact: true }).fill('Synthetic other window confirmed');
  64  |     await second.getByRole('checkbox', { name: 'I confirm these personal details; previous reports and requirement references remain in history.', exact: true }).check();
  65  |     const ack = second.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  66  |     await second.getByRole('button', { name: 'Save on server', exact: true }).click(); expect((await ack).status()).toBe(200);
  67  |     const conflict = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  68  |     await page.getByRole('button', { name: 'Save on server', exact: true }).click(); expect((await conflict).status()).toBe(409);
  69  |     await expect(recovery.getByText('Data changed. Review the saved version before creating a new request.', { exact: true })).toBeVisible();
  70  |     current = await (await page.request.get(endpoint)).json(); expect(current.revision).toBe(2);
  71  |     expect(current.state.document_tasks[0].personal.label).toBe('Synthetic other window confirmed');
  72  |     await page.getByRole('button', { name: 'Close editor', exact: true }).click();
  73  |     await recovery.getByRole('button', { name: 'Refresh saved records', exact: true }).click();
  74  |   } finally { await secondContext.close(); }
  75  |   // Remove only the selected confirmed first receipt; the CAS request stays unresolved.
  76  |   await recovery.getByRole('checkbox').first().check();
  77  |   await recovery.getByRole('button', { name: 'Clear selected local confirmations', exact: true }).click();
  78  |   await expect(recovery.getByRole('checkbox')).toHaveCount(0);
  79  |   for (let index = 0; index < 63; index++) {
  80  |     await editor(page, `Synthetic cap task ${index}`);
  81  |     const ack = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  82  |     await page.getByRole('button', { name: 'Save on server', exact: true }).click(); expect((await ack).status()).toBe(200);
  83  |     await expect(page.getByTestId('personal-document-task').filter({ has: page.getByRole('heading', { name: `Synthetic cap task ${index}`, exact: true }) })).toHaveCount(1);
  84  |   }
  85  |   await expect(recovery.getByText('The local journal has 64 entries. A new request needs space; only selected confirmed entries can be cleared.', { exact: true })).toBeVisible();
  86  |   const physical = await page.evaluate((id: string) => {
  87  |     const rows = Object.keys(localStorage).map(key => ({ key, raw: localStorage.getItem(key)! })).flatMap(row => {
  88  |       try { return [{ ...row, value: JSON.parse(row.raw) }]; } catch { return []; }
  89  |     });
  90  |     return rows.find(row => row.value?.schema_version === 'g3-case-local-index-v1' && row.value.profile_id === id);
  91  |   }, profile.id);
  92  |   expect(physical?.value.entries).toHaveLength(64);
  93  |   const countBefore = bodies.length; const revisionBefore = (await (await page.request.get(endpoint)).json()).revision;
  94  |   await editor(page, 'Synthetic blocked65th'); await page.getByRole('button', { name: 'Save on server', exact: true }).click();
  95  |   await expect(page.getByText('Saving has not been confirmed. Keep the original request in recovery; do not create a duplicate.', { exact: true })).toBeVisible();
  96  |   expect(bodies).toHaveLength(countBefore); expect((await (await page.request.get(endpoint)).json()).revision).toBe(revisionBefore);
  97  |   await page.getByRole('button', { name: 'Close editor', exact: true }).click();
> 98  |   await recovery.getByRole('checkbox').first().check(); await recovery.getByRole('button', { name: 'Clear selected local confirmations', exact: true }).click();
      |                                                ^ TimeoutError: locator.check: Timeout 20000ms exceeded.
  99  |   await editor(page, 'Synthetic new request after selected cleanup');
  100 |   const ack = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  101 |   await page.getByRole('button', { name: 'Save on server', exact: true }).click(); expect((await ack).status()).toBe(200);
  102 |   await page.reload(); await expect(recovery.getByText('Data changed. Review the saved version before creating a new request.', { exact: true })).toBeVisible();
  103 |   const beforeCorrupt = await page.evaluate((key: string) => localStorage.getItem(key), physical!.key);
  104 |   await page.evaluate((key: string) => localStorage.setItem(key, 'null'), physical!.key); await page.reload();
  105 |   await expect(page.getByRole('button', { name: 'Add a document task', exact: true })).toBeDisabled();
  106 |   expect(await page.evaluate((key: string) => localStorage.getItem(key), physical!.key)).toBe('null');
  107 |   expect((await (await page.request.get(endpoint)).json()).revision).toBe(revisionBefore + 1);
  108 |   // Restore only this test's exact preimage; this is fixture cleanup, not product recovery.
  109 |   await page.evaluate(({ key, raw }) => localStorage.setItem(key, raw), { key: physical!.key, raw: beforeCorrupt! });
  110 |   await info.attach('native-recovery-proof.json', { body: JSON.stringify({ auth, profile_id: profile.id, original_uuid: write.client_write_uuid, replay_event: originalReceipt?.event_id, cas_status: 409, physical_entries: 64, blocked_without_http: true, pending_preserved: true, corrupt_bytes_preserved: true, accepted_revision: revisionBefore + 1 }), contentType: 'application/json' });
  111 | });
  112 | 
```