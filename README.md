# 🛒 Customer Support Chatbot (GenAI + Serverless)

This project builds a **serverless customer support chatbot** using **AWS CDK (Python)**.
It integrates **Amazon Bedrock (Llama 3 Instruct)** with a **FAQ database (DynamoDB)** and a **Knowledge Base (S3)** to answer customer queries in real-time through an **API Gateway + Lambda** setup.

---

## 📌 Architecture

**Flow:**

1. Customer sends a query → **API Gateway (POST /chat)**
2. Request goes to **Lambda (Chatbot)**

   * Checks **FAQ table (DynamoDB)** for an exact match
   * Loads **knowledge base documents (S3)** as context
   * Calls **Amazon Bedrock (Llama 3 Instruct)** for AI response
3. Response returned to the user with source (`faq` or `bedrock`)

**AWS Services Used:**

* **Amazon API Gateway** → REST endpoint for chatbot queries
* **AWS Lambda** → Orchestrates FAQ lookup + Bedrock call
* **Amazon DynamoDB** → Stores FAQ Q\&A pairs
* **Amazon S3** → Stores knowledge base documents (e.g., return policy, shipping guide)
* **Amazon Bedrock** → Provides GenAI response (Llama 3 Instruct)

---

## 📂 Project Structure

```
serverless-chatbot/
├── app.py                  # CDK entry point
├── serverless_app_stack.py # CDK Stack (infra)
├── requirements.txt        # Python dependencies
└── kb/                     # Knowledge base docs (uploaded to S3)
    ├── loyalty_program.txt
    ├── return_policy.txt
    └── shipping_guide.txt
```

---

## ⚙️ How to Create this Project

1. **Clone & setup environment**

   ```bash
   git clone <your-repo-url> serverless-chatbot
   cd serverless-chatbot
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Initialize CDK project**

   ```bash
   cdk init app --language python
   ```

3. **Add dependencies**

   ```bash
   pip install aws-cdk-lib constructs boto3
   ```

4. **Add knowledge base docs**
   Create a folder `kb/` and add text files like:

   ```
   loyalty_program.txt
   return_policy.txt
   shipping_guide.txt
   ```

5. **Bootstrap & deploy**

   ```bash
   cdk bootstrap
   cdk deploy
   ```

---

## 🧩 Details About This Project

* **FAQ Table (DynamoDB)** → Preloaded with sample FAQs:

  * “What is your return policy?”
  * “Do you ship internationally?”
  * “What payment methods are accepted?”

* **Knowledge Base (S3)** → Stores longer reference docs:

  * `loyalty_program.txt` → Explains customer loyalty program
  * `return_policy.txt` → Company return policy
  * `shipping_guide.txt` → Shipping details

* **Lambda**:

  * First tries **FAQ lookup** in DynamoDB
  * If not found, loads S3 docs and calls **Bedrock Llama 3 Instruct** with proper `[INST] ... [/INST]` format
  * Returns response with `{"query": "...", "answer": "...", "source": "faq|bedrock"}`

* **Amazon Bedrock**:

  * Uses **Meta Llama 3 Instruct (70B or 8B)**
  * You must have access granted in **Bedrock console**

---

## 🔍 How to Test

1. Get your API endpoint from CDK output:

   ```bash
   ApiUrl = https://<api-id>.execute-api.<region>.amazonaws.com/prod/chat
   ```

2. Send queries via `curl`:

   ```bash
   curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"query": "What are the shipping options?"}' \
     https://<api-id>.execute-api.<region>.amazonaws.com/prod/chat
   ```

   ✅ Example Response:

   ```json
   {
     "query": "What are the shipping options?",
     "answer": "We offer free standard shipping on orders over $50. Express shipping is also available at checkout. International orders take 7–14 business days.",
     "source": "bedrock"
   }
   ```

3. Test an **FAQ** question:

   ```bash
   curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"query": "Do you ship internationally?"}' \
     https://<api-id>.execute-api.<region>.amazonaws.com/prod/chat
   ```

   ✅ Example Response:

   ```json
   {
     "query": "Do you ship internationally?",
     "answer": "Yes—we ship to 50+ countries. Delivery times vary by country.",
     "source": "faq"
   }
   ```

---
