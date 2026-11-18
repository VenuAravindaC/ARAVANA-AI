# 🎯 CUSTOM CLASSIFICATION RULES - Industry Examples

**Updated:** 2026-11-15  
**Feature:** Customizable HOT/WARM/COLD/NEW criteria per client

---

## 🏠 **REAL ESTATE BROKER**

```
CLASSIFICATION RULES:
- HOT: Has clear budget + wants to visit within 7 days OR has loan pre-approved OR says "ready to buy" OR asks for immediate site visit
- WARM: Interested in specific property type, has budget range but timeline is "next month" or "exploring options"
- COLD: Just browsing, no budget mentioned, says "just checking prices" or unresponsive after 2+ messages
- NEW: Initial inquiry asking about availability or location, not enough info yet
```

**Example HOT Lead:**
> "I need 3BHK in Whitefield. Budget 80 lakhs. Loan approved. Can I visit this Saturday?"

**Example WARM Lead:**
> "Looking for 2BHK apartments. Budget around 50-60 lakhs. Planning to buy in next 2-3 months."

---

## 🍕 **RESTAURANT (Table Booking)**

```
CLASSIFICATION RULES:
- HOT: Wants to book for today OR tomorrow OR party size 8+ people OR says "urgent" OR special occasion (birthday/anniversary)
- WARM: Asking about menu or availability for next week OR inquiring about private dining
- COLD: General questions about cuisine, location, parking without booking intent
- NEW: Initial "Are you open?" or "What time do you close?" inquiry
```

**Example HOT Lead:**
> "Need table for 10 people tonight at 8pm. It's my wife's birthday."

**Example WARM Lead:**
> "Do you have a private dining area? Planning a dinner next Friday for 6 people."

---

## 💼 **B2B SaaS / Software**

```
CLASSIFICATION RULES:
- HOT: Decision maker (CEO/CTO), clear budget, wants demo THIS week OR already using competitor OR says "we need this urgently"
- WARM: Interested, doing research, timeline is "next quarter" OR mid-level employee (not decision maker) OR evaluating 3+ options
- COLD: Student, tire-kicker, "just exploring", no company mentioned, or unresponsive
- NEW: Initial "Do you offer X feature?" or pricing inquiry without context
```

**Example HOT Lead:**
> "I'm the CTO at ABC Corp. We're currently using [Competitor] but facing issues. Need to migrate in 2 weeks. Budget approved. Can we do a demo tomorrow?"

**Example WARM Lead:**
> "I'm exploring project management tools for our 20-person team. What's your pricing? We're evaluating 3 options."

---

## 🎓 **COACHING / EDUCATION**

```
CLASSIFICATION RULES:
- HOT: Wants to join current batch OR asks "when is next batch starting?" OR says "I'm ready to enroll" OR budget confirmed
- WARM: Interested in course details, asking about curriculum, timeline is "next month" or "after exams"
- COLD: Just browsing, "I'll think about it", no timeline, or ghost after sending details
- NEW: Initial "What courses do you offer?" or "Is online available?" inquiry
```

**Example HOT Lead:**
> "I want to join your data science bootcamp. When does the next batch start? What's the fee?"

**Example WARM Lead:**
> "Interested in your digital marketing course. Can you send the syllabus? I'm planning to start after my semester ends in 2 months."

---

## 🏋️ **GYM / FITNESS CENTER**

```
CLASSIFICATION RULES:
- HOT: Wants to visit gym TODAY or TOMORROW OR asks about joining this week OR mentions specific fitness goal with deadline (wedding in 2 months)
- WARM: Asking about membership plans, timings, trainers but no immediate visit planned
- COLD: "What are your fees?" without follow-up OR unresponsive OR says "I'll come when I have time"
- NEW: Initial "Where are you located?" or "Are you open on Sundays?"
```

**Example HOT Lead:**
> "I need to lose 10kg before my wedding in 3 months. Can I visit today evening? What's your personal training cost?"

**Example WARM Lead:**
> "Looking for a gym near my office. What are your membership plans?"

---

## 🏥 **DENTAL CLINIC**

```
CLASSIFICATION RULES:
- HOT: Has pain/emergency OR wants appointment within 2 days OR says "urgent" OR specific procedure needed (root canal, extraction)
- WARM: Routine checkup inquiry, asking about teeth whitening/braces, timeline flexible (next week or later)
- COLD: General inquiry about services, no specific problem, or unresponsive
- NEW: Initial "Do you accept insurance?" or "What are your timings?"
```

**Example HOT Lead:**
> "I have severe toothache since yesterday. Can I get an appointment today or tomorrow?"

**Example WARM Lead:**
> "Interested in teeth whitening. What's the cost? Can I schedule next week?"

---

## 🏠 **HOME SERVICES (Plumber/Electrician)**

```
CLASSIFICATION RULES:
- HOT: Emergency (leaking pipe, power outage) OR needs service TODAY or TOMORROW OR says "urgent"
- WARM: Planning future work (renovation, AC installation), timeline next week or later
- COLD: "How much do you charge?" without specific problem OR quote shopping
- NEW: Initial "Do you cover [area]?" or "Are you available?"
```

**Example HOT Lead:**
> "Water pipe burst in my kitchen! Can you come today? It's flooding."

**Example WARM Lead:**
> "Planning to install 3 ACs next month. Can you give me a quote?"

---

## 🚗 **CAR DEALERSHIP**

```
CLASSIFICATION RULES:
- HOT: Has trade-in car OR loan approved OR wants test drive THIS week OR asks "what's your best price for immediate purchase?"
- WARM: Comparing 2-3 models, asking about EMI options, timeline is "next month" or "after bonus"
- COLD: "Send me brochure", no test drive interest, or unresponsive
- NEW: Initial "Is [model] available?" or "What's the on-road price?"
```

**Example HOT Lead:**
> "I want to buy the XUV700. I have my old car for exchange. Loan approved. Can I test drive tomorrow?"

**Example WARM Lead:**
> "Comparing XUV700 vs Creta. What's your EMI for 5 years? I'm planning to buy in 2 months."

---

## 📊 **HOW TO CONFIGURE (In Supabase Client Record)**

Add a `classification_rules` column to your `clients` table:

```sql
ALTER TABLE clients ADD COLUMN classification_rules TEXT;
```

Then when onboarding a client, insert their industry-specific rules:

```json
{
  "business_name": "ABC Realty",
  "classification_rules": "- HOT: Has clear budget + wants to visit within 7 days OR has loan pre-approved\n- WARM: Interested in specific property type, timeline next month\n- COLD: Just browsing, no budget\n- NEW: Initial inquiry"
}
```

---

## ✅ **FALLBACK (If Not Configured)**

If a client doesn't have custom rules, the system uses the **default real estate rules** (since that's your primary market).

---

## 🎯 **WHY THIS MATTERS (Your Sales Pitch)**

**Other AI agencies:**
> "We classify leads as hot or cold."

**YOU:**
> "My AI uses YOUR definition of a hot lead. Real estate hot lead ≠ restaurant hot lead. You tell me what makes a lead urgent for YOUR business, and the AI follows that. Fully customized."

**This is a HUGE competitive advantage.** 🔥

---

## 📝 **NEXT STEPS**

1. ✅ Code updated to support `classification_rules` per client
2. 🔜 Add `classification_rules` column to Supabase `clients` table
3. 🔜 During onboarding, ask client: "What makes a lead HOT for your business?"
4. 🔜 Store their rules in their client record
5. ✅ AI automatically applies their custom criteria

---

**This feature alone justifies premium pricing (₹28K/month tier).** 💰
