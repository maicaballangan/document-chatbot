from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "user" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "email" VARCHAR(100) NOT NULL UNIQUE,
    "first_name" VARCHAR(100) NOT NULL,
    "last_name" VARCHAR(100) NOT NULL,
    "password" VARCHAR(255) NOT NULL,
    "last_login" TIMESTAMPTZ,
    "is_active" BOOL NOT NULL  DEFAULT False,
    "is_staff" BOOL NOT NULL  DEFAULT False,
    "is_superuser" BOOL NOT NULL  DEFAULT False,
    "register_token" VARCHAR(50),
    "invite_token" VARCHAR(255),
    "stripe_customer_id" VARCHAR(50)  UNIQUE
);
CREATE TABLE IF NOT EXISTS "document" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "created_by" BIGINT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "status" VARCHAR(12) NOT NULL,
    "product" VARCHAR(9) NOT NULL,
    "path" VARCHAR(255) NOT NULL  DEFAULT '/',
    "url" VARCHAR(255),
    "extract_duration" DOUBLE PRECISION,
    "total_pages" INT,
    "size" BIGINT,
    "task_id" VARCHAR(100),
    "vector_id" VARCHAR(100),
    "summary_id" VARCHAR(100),
    "content" JSONB
);
COMMENT ON COLUMN "document"."status" IS 'PENDING: pending\nSUCCESS: success\nINVALID: invalid\nFAILED: failed\nFAILED_QUEUE: failed_queue';
COMMENT ON COLUMN "document"."product" IS 'GENERAL: general\nPOLICY: policy\nDISCOVERY: discovery';
CREATE TABLE IF NOT EXISTS "policy" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "created_by" BIGINT NOT NULL,
    "name" VARCHAR(255),
    "summary" JSONB,
    "report" JSONB,
    "type" VARCHAR(255),
    "document_id" UUID NOT NULL REFERENCES "document" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "chat_session" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "created_by" BIGINT NOT NULL,
    "name" VARCHAR(50),
    "documents_json" JSONB NOT NULL,
    "product" VARCHAR(9) NOT NULL,
    "product_id" UUID
);
COMMENT ON COLUMN "chat_session"."product" IS 'GENERAL: general\nPOLICY: policy\nDISCOVERY: discovery';
CREATE TABLE IF NOT EXISTS "chat" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "created_by" BIGINT,
    "content" TEXT NOT NULL,
    "role" VARCHAR(9) NOT NULL,
    "response_to" UUID,
    "is_liked" BOOL,
    "is_bookmarked" BOOL,
    "bookmark_name" TEXT,
    "source_info" JSONB,
    "session_id" UUID NOT NULL REFERENCES "chat_session" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "chat"."role" IS 'USER: user\nASSISTANT: assistant';
CREATE TABLE IF NOT EXISTS "helpfulquestion" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "question" VARCHAR(255) NOT NULL,
    "answer" VARCHAR(255) NOT NULL  DEFAULT '',
    "status" VARCHAR(7) NOT NULL
);
COMMENT ON COLUMN "helpfulquestion"."status" IS 'GENERAL: general\nPOLICY: policy';
CREATE TABLE IF NOT EXISTS "subscription_plan" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(100) NOT NULL UNIQUE,
    "credits" INT   DEFAULT 0,
    "document_limit" INT,
    "question_limit" INT,
    "storage_limit" BIGINT,
    "descriptions" JSONB,
    "is_consular" BOOL NOT NULL  DEFAULT False,
    "trial_period" INT,
    "document_size_limit" BIGINT,
    "ocr_support" BOOL NOT NULL  DEFAULT False,
    "chat_with_files" BOOL NOT NULL  DEFAULT True,
    "chat_with_folders" BOOL NOT NULL  DEFAULT False,
    "invite_team" BOOL NOT NULL  DEFAULT False,
    "maximum_member" INT,
    "policy_analyzer_report_card" BOOL NOT NULL  DEFAULT False,
    "discovery_tool_interrogatories" BOOL NOT NULL  DEFAULT False,
    "customer_support_email" BOOL NOT NULL  DEFAULT False,
    "customer_support_phone" BOOL NOT NULL  DEFAULT False,
    "support_turnaround" INT,
    "support_mycase" BOOL NOT NULL  DEFAULT False,
    "stripe_product_id" VARCHAR(50) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS "subscription_price" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "is_deleted" BOOL NOT NULL  DEFAULT False,
    "stripe_price_id" VARCHAR(50) NOT NULL UNIQUE,
    "billing_cycle" VARCHAR(7) NOT NULL,
    "amount" DECIMAL(10,2) NOT NULL,
    "currency" VARCHAR(3) NOT NULL,
    "subscription_plan_id" BIGINT NOT NULL REFERENCES "subscription_plan" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "subscription_price"."billing_cycle" IS 'MONTHLY: monthly\nANNUAL: annual';
COMMENT ON COLUMN "subscription_price"."currency" IS 'AFN: AFN\nEUR: EUR\nALL: ALL\nDZD: DZD\nUSD: USD\nAOA: AOA\nXCD: XCD\nARS: ARS\nAMD: AMD\nAWG: AWG\nAUD: AUD\nAZN: AZN\nBSD: BSD\nBHD: BHD\nBDT: BDT\nBBD: BBD\nBYN: BYN\nBZD: BZD\nXOF: XOF\nBMD: BMD\nINR: INR\nBTN: BTN\nBOB: BOB\nBOV: BOV\nBAM: BAM\nBWP: BWP\nNOK: NOK\nBRL: BRL\nBND: BND\nBGN: BGN\nBIF: BIF\nCVE: CVE\nKHR: KHR\nXAF: XAF\nCAD: CAD\nKYD: KYD\nCLP: CLP\nCLF: CLF\nCNY: CNY\nCOP: COP\nCOU: COU\nKMF: KMF\nCDF: CDF\nNZD: NZD\nCRC: CRC\nCUP: CUP\nCUC: CUC\nANG: ANG\nCZK: CZK\nDKK: DKK\nDJF: DJF\nDOP: DOP\nEGP: EGP\nSVC: SVC\nERN: ERN\nSZL: SZL\nETB: ETB\nFKP: FKP\nFJD: FJD\nXPF: XPF\nGMD: GMD\nGEL: GEL\nGHS: GHS\nGIP: GIP\nGTQ: GTQ\nGBP: GBP\nGNF: GNF\nGYD: GYD\nHTG: HTG\nHNL: HNL\nHKD: HKD\nHUF: HUF\nISK: ISK\nIDR: IDR\nXDR: XDR\nIRR: IRR\nIQD: IQD\nILS: ILS\nJMD: JMD\nJPY: JPY\nJOD: JOD\nKZT: KZT\nKES: KES\nKPW: KPW\nKRW: KRW\nKWD: KWD\nKGS: KGS\nLAK: LAK\nLBP: LBP\nLSL: LSL\nZAR: ZAR\nLRD: LRD\nLYD: LYD\nCHF: CHF\nMOP: MOP\nMKD: MKD\nMGA: MGA\nMWK: MWK\nMYR: MYR\nMVR: MVR\nMRU: MRU\nMUR: MUR\nXUA: XUA\nMXN: MXN\nMXV: MXV\nMDL: MDL\nMNT: MNT\nMAD: MAD\nMZN: MZN\nMMK: MMK\nNAD: NAD\nNPR: NPR\nNIO: NIO\nNGN: NGN\nOMR: OMR\nPKR: PKR\nPAB: PAB\nPGK: PGK\nPYG: PYG\nPEN: PEN\nPHP: PHP\nPLN: PLN\nQAR: QAR\nRON: RON\nRUB: RUB\nRWF: RWF\nSHP: SHP\nWST: WST\nSTN: STN\nSAR: SAR\nRSD: RSD\nSCR: SCR\nSLE: SLE\nSGD: SGD\nXSU: XSU\nSBD: SBD\nSOS: SOS\nSSP: SSP\nLKR: LKR\nSDG: SDG\nSRD: SRD\nSEK: SEK\nCHE: CHE\nCHW: CHW\nSYP: SYP\nTWD: TWD\nTJS: TJS\nTZS: TZS\nTHB: THB\nTOP: TOP\nTTD: TTD\nTND: TND\nTRY: TRY\nTMT: TMT\nUGX: UGX\nUAH: UAH\nAED: AED\nUSN: USN\nUYU: UYU\nUYI: UYI\nUYW: UYW\nUZS: UZS\nVUV: VUV\nVES: VES\nVED: VED\nVND: VND\nYER: YER\nZMW: ZMW\nZWL: ZWL\nZWG: ZWG\nXBA: XBA\nXBB: XBB\nXBC: XBC\nXBD: XBD\nXTS: XTS\nXXX: XXX\nXAU: XAU\nXPD: XPD\nXPT: XPT\nXAG: XAG';
CREATE TABLE IF NOT EXISTS "subscription" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "status" VARCHAR(10) NOT NULL,
    "current_period_start" TIMESTAMPTZ,
    "current_period_end" TIMESTAMPTZ,
    "trial_period_end" TIMESTAMPTZ,
    "expired_at" TIMESTAMPTZ,
    "canceled_at" TIMESTAMPTZ,
    "stripe_subscription_id" VARCHAR(100) NOT NULL UNIQUE,
    "subscription_price_id" BIGINT REFERENCES "subscription_price" ("id") ON DELETE SET NULL,
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "subscription"."status" IS 'TRIAL: trial\nACTIVE: active\nCANCELED: canceled\nINCOMPLETE: incomplete\nINCOMPLETE_EXPIRED: expired\nPAST_DUE: past_due\nUNPAID: unpaid\nPAUSED: paused';
CREATE TABLE IF NOT EXISTS "invoice" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "stripe_invoice_id" VARCHAR(255) NOT NULL UNIQUE,
    "attempt_count" INT NOT NULL  DEFAULT 1,
    "next_payment_attempt" TIMESTAMPTZ,
    "amount" DECIMAL(10,2) NOT NULL,
    "currency" VARCHAR(3) NOT NULL  DEFAULT 'USD',
    "status" VARCHAR(13) NOT NULL,
    "payment_status" VARCHAR(15) NOT NULL,
    "paid_at" TIMESTAMPTZ,
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "invoice"."status" IS 'PAID: paid\nFAILED: failed\nDRAFT: draft\nOPEN: open\nUNCOLLECTIBLE: uncollectible\nVOID: void';
COMMENT ON COLUMN "invoice"."payment_status" IS 'SUCCESS: success\nFAILED: failed\nUNPAID: unpaid\nACTION_REQUIRED: action_required';
CREATE TABLE IF NOT EXISTS "chat_session_user" (
    "chat_session_id" UUID NOT NULL REFERENCES "chat_session" ("id") ON DELETE NO ACTION,
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE NO ACTION
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_chat_sessio_chat_se_1788a4" ON "chat_session_user" ("chat_session_id", "user_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
