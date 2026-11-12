# Stage R: research findings (2026-11-12)

Desk research from public web sources. **Nothing was purchased, registered or
signed up for.** Prices are indicative, taken from the sources linked, and
must be confirmed on the vendor's own page before any commitment. Items marked
⚠ could not be verified from this environment.

## 1. Wake word: Porcupine and "Hey JARVIS"

| Question | Finding |
|----------|---------|
| Can Porcupine detect it? | Yes. "Jarvis" is one of Porcupine's built-in keywords, and Picovoice's own web tutorial trains "Hey Jarvis" as a custom phrase for the Web (WASM) platform. [SDK keyword list](https://npmjs.com/package/@picovoice/porcupine-node) · [Web tutorial](https://picovoice.ai/blog/how-to-add-custom-wake-words-to-any-web-app) |
| Browser support | Web (WASM) is a supported platform, which matches our design (on-device, foreground only). |
| Licence | ⚠ **Main risk.** Picovoice's free tier is reported to end after 30 June 2026, so commercial use needs a paid plan. Custom wake-word files carry commercial-use restrictions. One third-party listing puts the Enterprise plan from USD 30,000 a year; Picovoice does not publish a simple small-business price. [Free-tier notice](https://community.home-assistant.io/t/fyi-picovoice-confirmed-free-tier-accesskeys-will-stop-working-after-june-30-2026/1012744) · [Pricing page](https://picovoice.ai/pricing) · [Third-party listing](https://us.fitgap.com/products/003875/picovoice-voice-ai) |

**Recommendation:** before paying, ask Picovoice for a written quote for one
to five web users with the "Hey Jarvis" phrase. If the quote is out of
proportion for a single-user feature, the options are:

- keep push-to-talk only (already built)
- ask me to assess an open-source engine

The wake-word code sits behind an interface, so either choice is possible.
**Decision needed after the quote.**

## 2. Voice shortlist (text-to-speech)

| Provider | Why it is on the list | Indicative price | Notes |
|----------|----------------------|------------------|-------|
| **ElevenLabs** | Widely treated as the quality benchmark; large library of deep male voices | About USD 50 per million characters (Flash/Turbo), USD 100 (Multilingual). About 75 ms claimed latency on Flash. | Subscription tiers. Check that the chosen voice's licence allows commercial use. [Source](https://techsy.io/en/blog/best-tts-apis-developers) |
| **Azure AI Speech** | Same vendor as the proposed hosting; lowest cost; one contract | USD 16 per million characters (Neural), USD 22 (Neural HD). 500,000 characters a month free. | Good fit with Microsoft 365 and Azure. [Source](https://techsy.io/en/blog/best-tts-apis-developers) |
| **Cartesia Sonic** | Fastest response (about 40 ms to first audio) | About USD 38–39 per million characters | Commercial licence starts at the Pro plan, not the free plan. [Latency](https://futureagi.com/blog/best-text-to-speech-providers-2026/) · [Licence note](https://invideo.io/blog/ai-voice-model-pricing/) |

Rough cost at ten hours of spoken replies a month (about 150,000 characters;
my arithmetic from the prices above): Azure HD about USD 3, Cartesia about
USD 6, ElevenLabs USD 8–15. Cost is not the deciding factor at this volume;
the voice is.

**Speech-to-text:** choose it with the voice. Azure Speech covers both. This
keeps to one vendor if Azure is chosen.

**Audition:** I need your approval to create trial accounts with these three
providers (no payment). I will then render the same short script in two or
three deep male voices from each and send you the audio files. No voice will
imitate an actor or character.

## 3. Trademarks (preliminary search, not a legal opinion)

### JARVIS

- Marvel Characters, Inc. holds a live United States registration for JARVIS
  in Class 9 (software for personal digital assistants), registration
  4737881, renewed in May 2025. [Record](https://markinton.com/trademark/jarvis-86294162)
- Marvel has opposed at least one other company's JARVIS software filing.
  [Report](https://www.goodmans.ca/insights/post/goodmans-ip-blog/marvel-and-nimbix-oppose-blackberry-jarvis-trademark)
- Several other companies hold or have applied for JARVIS marks for software
  and services (Classes 9 and 42). The field is crowded.
  [Listing](https://gleanmark.com/search?q=JARVIS)

**Assessment:** using "JARVIS" as an internal assistant name inside your own
company system is low-profile, but it gives you no rights in the name. Selling
or advertising a product or service under the name carries a real risk of
objection. **Recommendation:** keep JARVIS internal only. If AVEN GLOBAL ever
markets the assistant, choose an original name first. The name is one setting
in the system.

### AVEN GLOBAL

- "AVEN" alone is registered in the United States by unrelated companies for
  tools and optical instruments, and for financial services.
  [Record](https://markinton.com/trademark/aven-87715296)
- A stylised "AVE GLOBAL" mark is registered in the United States.
  [Record](https://trademark.justia.com/792/02/g-e-79202736.html)
- "AVENIR GLOBAL" is a Canadian communications group with a similar name.
  [Site](https://avenir.global/about-the-firm/)
- This search found no "AVEN GLOBAL" mark for procurement, trading or
  distribution. ⚠ It did not cover the Malawi register, which is not
  searchable online from here.

**Malawi route:** trademarks are registered at the Department of the Registrar
General. Malawi is also in ARIPO (Banjul Protocol) and joined the Madrid
Protocol on 25 December 2018, so regional and international filings are
possible later. Malawi uses one application per class.
[WIPO](https://www.wipo.int/about-wipo/en/offices/japan/news/2018/news_0069.html) · [Overview](https://inventa.com/en/malawi)

**Next step (needs your approval, has a fee):** a formal search at the
Registrar General for the name and logo in Class 35 (procurement and trading
services) and Class 39 (transport and distribution), by a Malawi IP
practitioner. Then file if clear.

## 4. Hosting: Azure South Africa North

- Azure Database for PostgreSQL (Flexible Server) is available in South Africa
  North. [Microsoft](https://learn.microsoft.com/azure/postgresql/overview)
- Indicative database price there: a 2-vCPU General Purpose server at about
  USD 0.225 an hour (about USD 165 a month), and about double with a
  high-availability standby. [Source](https://sparecores.com/database/azure/Standard_D2s_v3)
- ⚠ Not yet verified: Azure Container Apps and Managed Redis availability and
  prices in this region, and the cheaper burstable database price there.

**Rough monthly estimate (mine, to be confirmed in the Azure pricing
calculator):**

| Setup | What it includes | Estimate |
|-------|------------------|----------|
| Starter | Small burstable database with backups, two small app containers, small Redis, storage, no standby | USD 150–250 |
| Production | General Purpose database with standby, two replicas of each app, Redis, storage, monitoring | USD 450–700 |

The comparison with AWS Cape Town and Google Cloud Johannesburg needs the
three pricing calculators. I will prepare it as a costed sheet next; it does
not need any account.

## 5. Monitoring

| Need | Proposal | Indicative price |
|------|----------|------------------|
| Application errors | Sentry, Team plan | USD 26 a month billed yearly (USD 29 monthly); includes 50,000 errors and one uptime monitor. [Source](https://cubeapm.com/blog/sentry-pricing-review/) |
| Uptime checks and alerts to you | Better Stack | Free tier: 10 monitors with email and Slack alerts. [Source](https://betterstack.com/pricing?facet1=pdf) |
| Servers, database, backups | Azure Monitor alerts, if Azure is chosen | ⚠ Usage-based; to be costed with the hosting |

**Recommendation:** Sentry Team plus the Better Stack free tier, about USD 26
a month, with Azure's own alerts for database and backup failures.

## 6. Domain names

- ⚠ `avenglobal.com` and `avenglobal.mw`: availability could not be checked
  from this environment (registry look-ups are blocked here). Please check at
  any registrar, or tell me to check through the browser.
- `.mw` names are run by Malawi SDNP and sold through accredited registrars;
  any person or company may register. International resellers quote roughly
  USD 60–190 a year, some with a two-year minimum; local registrars are listed
  at nic.mw. [Policy](https://registrar.mw/policies/SDNP-dot-MW-Domain-Registration-Policy-ver-1.5.pdf) · [Example price](https://www.dynadot.com/domain/mw)

## 7. Exchange rates: Reserve Bank of Malawi

- The Reserve Bank publishes official rates once per business day.
- Two services republish them in a form software can read: Frankfurter (free,
  open source) and AllRatesToday (latest rates free, history from EUR 4.99 a
  month). [Frankfurter](https://frankfurter.dev/providers/rbm/) · [AllRatesToday](https://allratestoday.com/central-bank-rates-api/rbm/)

**Recommendation for Stage 19:** fetch daily from one of these, store the
source and the Reserve Bank's publication date with every rate, compare
against the Reserve Bank's own page during testing, and keep manual entry as
the fallback. Historical rates stay immutable.

## Decisions requested

1. Ask Picovoice for a quote (I draft the email; you send it)?
2. Approve trial accounts (no payment) with ElevenLabs, Azure Speech and
   Cartesia for the voice audition?
3. Keep "JARVIS" as an internal-only name?
4. Approve a formal Malawi trademark search for AVEN GLOBAL (fee applies)?
5. Shall I prepare the costed hosting comparison sheet?
6. Approve the monitoring proposal in principle?
