# Harberger Patent Licensing — A Thorough Explanation

## The Problem With Current Patents

In the current system:
- An inventor files a patent and pays a small filing fee (~$1K)
- The patent lasts 20 years regardless of whether the inventor *does anything* with it
- To enforce the patent, the inventor must sue infringers — which costs millions
- "Patent trolls" buy up patents and do nothing but sue people
- Companies sit on patents to block competitors (no one can use the idea, but the inventor isn't using it either)
- The value of a patent is determined by litigation outcomes, not by how useful it actually is

**The core failure**: Patents have no carrying cost. Holding a patent and doing nothing with it costs the owner essentially nothing. This means useless patents sit forever and block useful ones.

## The Harberger Solution

Treat patents the same way the Liability State treats **land**: declare a value, pay tax on it, and anyone can buy it at that declared price.

### The Two Tiers

Instead of one value, the patent holder declares **two numbers**:

**Tier 1 — The Buyout Price (what it costs to buy the patent outright)**

This is what someone pays to own the entire patent. If you declare Tier 1 = $500K:
- You pay annual tax on $500K (say 3% = $15K/year)
- Anyone can post a bond to buy the patent from you for $500K
- If someone offers $500K, you have **14 days to refuse for free** (tax basis increases). After that, refusal costs **15%** of the offer price ($75K).

**Tier 2 — The Licensing Fee (what it costs to use the patent per unit)**

This is what anyone pays to *use* the patent without buying it. If you declare Tier 2 = $0.50/unit:
- Anyone selling a product that uses your patent pays you $0.50 per unit
- No negotiation, no lawsuit, no lawyer — just pay the declared rate
- You don't have to sue them; they're already paying

### Why Two Tiers?

Without Tier 2, the only way to use a patent is to buy it outright. That's expensive and kills incremental innovation. Without Tier 1, there's no way to buy the patent from someone who's sitting on it. Both are needed.

---

## Concrete Example: Alice's Milling Machine Patent

Alice invents a new type of high-speed milling head. She registers her patent on the Mercantile Registry:

| Field | Her Declaration |
|-------|-----------------|
| Tier 1 (Buyout) | $1,000,000 |
| Tier 2 (Licensing) | $10 per milling head sold |
| Annual Tax | 3% of Tier 1 = $30,000/year |

### Scenario A: Alice Commercializes It Herself

Alice builds and sells milling heads. Every one she sells, she pays herself the $10 licensing fee (this is just accounting — she keeps the money). The tax costs her $30K/year, but she's making $100K+ from selling milling heads. Net positive. The system works.

### Scenario B: Alice Doesn't Want to Manufacture

Alice just wants to invent and profit from licensing. Someone else builds milling heads using her patent. Every unit sold, Alice collects $10. If 50,000 units sell, she makes $500K in licensing revenue. She pays $30K in tax. She keeps $470K. She's happy.

### Scenario C: A Troll Buys Alice's Patent

Bob (a patent troll) buys Alice's patent at auction for $200K. Bob declares:

| Field | Bob's Declaration |
|-------|-------------------|
| Tier 1 (Buyout) | $10,000,000 |
| Tier 2 (Licensing) | $0.01 per unit |
| Annual Tax | 3% of $10M = $300,000/year |

Bob declares a huge Tier 1 so no one can buy the patent out from under him. He declares a tiny Tier 2 so no one actually pays him meaningful licensing fees. His plan is to sue people instead.

**What happens**: Bob pays $300K/year in tax for a patent that generates almost no licensing revenue ($0.01 × 0 units = $0). After one year, Bob is down $300K. After two years, $600K. Bob cannot sustain this. He must either:
- Lower Tier 1 (reducing his tax burden) — but then someone can buy the patent
- Raise Tier 2 (actually generating licensing income) — but then companies pay him and use the patent, which defeats trolling
- Sell the patent — which is what he should have done originally

**Patent trolling becomes impossible.** The holding cost destroys the business model.

### Scenario D: Alice Is Legit But a Rival Tries to Grief Her

Carol, Alice's competitor, wants to harass Alice. Carol posts a bid to buy Alice's patent at the declared $1M:

**Under pure Harberger (no Option Premium)**:
- Alice must sell. She loses her patent.
- Carol now owns the patent. Carol can sit on it, blocking Alice from using her own invention.
- Alice is ruined despite being the legitimate inventor.

**Under Harberger + Option Premium**:
- Carol posts a **90-day bond** at $1M. Her capital is locked.
- Alice has **14 days** to refuse for **free** — no penalty, but her tax basis jumps to ~$1M
- After 14 days, Alice can refuse by paying Carol **15%** of $1M = **$150K**
- Carol's capital is locked for up to 14+90 = **104 days max**

Now Carol's calculation changes:
- If Carol is a legitimate buyer who genuinely wants the patent: she risks nothing. If Alice refuses after the free window, Carol gets $150K profit. Either way Carol wins.
- If Carol is a griefing troll trying to hurt Alice: she risks tying up $1M for up to 104 days. If Alice refuses after the free window, Carol gets $150K — which is profit, not punishment. The griefing backfires: Carol *profits* from Alice's refusal.

**The Option Premium transforms griefing into a profitable event for the owner.** The only way to hurt Alice is to *buy the patent for real* — which means Carol must actually want the patent, not just harass Alice.

---

## Concrete Numbers: The Griefing Math

Let's compare: Carol tries to force Alice to sell her patent for $1M.

### Without Option Premium (just capital commitment):

- Carol ties up $1M for up to 104 days
- Carol loses ~$14K in alternative investment returns (~1.4% opportunity cost)
- Alice must sell her patent. Carol wins. Alice loses her invention.
- Cost to Carol: $14K. Benefit to Carol: destroys a competitor's patent. **Cheap griefing.**

### With Option Premium (15% penalty + 14-day free window):

- Carol ties up $1M for up to 104 days
- Carol loses ~$14K in opportunity cost (~1.4% at 5% annual)
- If Alice refuses in the free window (Days 1-14), Carol gets her bond back immediately. Alice's tax basis increases.
- If Alice refuses after the free window, Carol gets $150K (15% of $1M)
- Alice keeps her patent. Carol makes ~$136K net profit ($150K - $14K).
- Carol's griefing is *profitable*, which means it's not griefing — it's investment arbitrage

**Key insight**: The Option Premium doesn't just punish griefers — it makes the *defense* against griefing profitable for the owner. Alice can always refuse a hostile bid and come out ahead (she keeps the patent *and* the bidder pays her a penalty).

---

## How Bidding Wars Work (The "Exodus Equilibrium" for Patents)

Alice declares her patent at Tier 1 = $1M. A rival thinks it's worth $5M. The rival bids at $5M.

**Without Option Premium**: Alice must sell for $5M. Done.

**With Option Premium**:
- Rival posts a 90-day bond at $5M. Alice has 14 days to refuse for free (tax basis jumps). After that, refusal costs 15% ($750K).
- If Alice refuses, her patent now has an *imputed value* of ~$5M for tax purposes
- Alice pays tax on ~$5M instead of $1M going forward
- The system forces Alice to either sell (she gets paid the true value) or pay taxes reflecting the true value (she puts her money where her sentiment is)

This is the **Pride Tax** — the premium you pay to keep something you value above market price. If Alice truly believes the patent is worth $5M to her (sentimental attachment, strategic importance), she can keep it — but she pays the community for that privilege.

---

## Summary Table

| Concept | Plain English | Example |
|---------|---------------|---------|
| **Tier 1** | "How much to buy this patent?" | $1M |
| **Tier 2** | "How much per unit to use this patent?" | $10/unit |
| **Tax** | Annual fee for holding the patent | 3% of Tier 1 = $30K/year |
|| **Option** | &quot;I want to buy. You have 14 days to say no for free.&quot; | Buyer posts 90-day bond |
|| **Free Window** | &quot;I&apos;m saying no. No penalty, but my taxes go up.&quot; | 14 days, tax basis increases |
|| **Penalty** | &quot;I&apos;m saying no after the free window.&quot; | 15% of offer price |
|| **Pride Tax** | &quot;I&apos;m keeping it even though it&apos;s expensive.&quot; | Pay extra tax on imputed higher value |

Any of these still unclear? I can walk through more examples or different scenarios.
