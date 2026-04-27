-- CreateEnum
CREATE TYPE "Plan" AS ENUM ('free', 'analyst', 'enterprise');

-- CreateEnum
CREATE TYPE "Role" AS ENUM ('user', 'admin');

-- CreateEnum
CREATE TYPE "Layout" AS ENUM ('overview', 'trends', 'claims');

-- CreateEnum
CREATE TYPE "RiskLevel" AS ENUM ('low', 'medium', 'high');

-- CreateEnum
CREATE TYPE "ClaimType" AS ENUM ('factual', 'opinion', 'prediction', 'statistic');

-- CreateEnum
CREATE TYPE "Direction" AS ENUM ('rising', 'peaking', 'declining', 'stable');

-- CreateTable
CREATE TABLE "User" (
    "user_id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "name" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "initials" TEXT NOT NULL,
    "plan" "Plan" NOT NULL DEFAULT 'free',
    "role" "Role" NOT NULL DEFAULT 'user',
    "password" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "User_pkey" PRIMARY KEY ("user_id")
);

-- CreateTable
CREATE TABLE "Board" (
    "board_id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "user_id" UUID NOT NULL,
    "board_name" VARCHAR(500) NOT NULL,
    "description" VARCHAR(500),
    "search_terms" TEXT[],
    "layout" "Layout" NOT NULL DEFAULT 'overview',
    "last_updated_at" TIMESTAMP(3) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Board_pkey" PRIMARY KEY ("board_id")
);

-- CreateTable
CREATE TABLE "Channel" (
    "channel_id" VARCHAR(50) NOT NULL,
    "channel_name" VARCHAR(500) NOT NULL,
    "total_claims" INTEGER NOT NULL,
    "flagged_claims" INTEGER NOT NULL,
    "accuracy_rate" DOUBLE PRECISION NOT NULL,
    "risk_level" "RiskLevel" NOT NULL,
    "risk_score" DOUBLE PRECISION NOT NULL,
    "last_assessed_at" TIMESTAMP(3) NOT NULL,
    "processed_at" TIMESTAMP(3),

    CONSTRAINT "Channel_pkey" PRIMARY KEY ("channel_id")
);

-- CreateTable
CREATE TABLE "Video" (
    "video_id" VARCHAR(20) NOT NULL,
    "board_id" UUID NOT NULL,
    "channel_id" VARCHAR(50) NOT NULL,
    "title" VARCHAR(500) NOT NULL,
    "description" TEXT,
    "view_count" INTEGER NOT NULL,
    "duration_seconds" INTEGER,
    "published_at" TIMESTAMP(3) NOT NULL,
    "processed" BOOLEAN NOT NULL DEFAULT false,
    "processed_at" TIMESTAMP(3),

    CONSTRAINT "Video_pkey" PRIMARY KEY ("video_id","board_id")
);

-- CreateTable
CREATE TABLE "Claim" (
    "claim_id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "video_id" VARCHAR(20) NOT NULL,
    "narrative_id" TEXT,
    "video_title" VARCHAR(500) NOT NULL,
    "claim_text" TEXT NOT NULL,
    "claim_type" "ClaimType" NOT NULL,
    "confidence_score" DOUBLE PRECISION NOT NULL,
    "risk_level" "RiskLevel" NOT NULL,
    "processed_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "is_verified" BOOLEAN NOT NULL,
    "accuracy_rating" DOUBLE PRECISION,

    CONSTRAINT "Claim_pkey" PRIMARY KEY ("claim_id")
);

-- CreateTable
CREATE TABLE "Narrative" (
    "narrative_id" TEXT NOT NULL,
    "board_id" UUID NOT NULL,
    "title" VARCHAR(500) NOT NULL,
    "summary" TEXT,
    "topic_label" VARCHAR(200),
    "claim_count" INTEGER NOT NULL DEFAULT 0,
    "color" TEXT NOT NULL,
    "first_seen_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_seen_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Narrative_pkey" PRIMARY KEY ("narrative_id","board_id")
);

-- CreateTable
CREATE TABLE "Trend" (
    "trend_id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "board_id" UUID NOT NULL,
    "labels" TEXT[],
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Trend_pkey" PRIMARY KEY ("trend_id")
);

-- CreateTable
CREATE TABLE "TrendData" (
    "dataset_id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "trend_id" UUID NOT NULL,
    "narrative_id" TEXT NOT NULL,
    "label" VARCHAR(50) NOT NULL,
    "color" VARCHAR(50) NOT NULL,
    "data" INTEGER[],
    "direction" "Direction" NOT NULL,

    CONSTRAINT "TrendData_pkey" PRIMARY KEY ("dataset_id")
);

-- CreateTable
CREATE TABLE "BoardChannel" (
    "board_id" UUID NOT NULL,
    "channel_id" VARCHAR(50) NOT NULL,
    "processed_at" TIMESTAMP(3),

    CONSTRAINT "BoardChannel_pkey" PRIMARY KEY ("board_id","channel_id")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE UNIQUE INDEX "Video_video_id_key" ON "Video"("video_id");

-- CreateIndex
CREATE UNIQUE INDEX "Narrative_narrative_id_key" ON "Narrative"("narrative_id");

-- CreateIndex
CREATE UNIQUE INDEX "TrendData_trend_id_narrative_id_key" ON "TrendData"("trend_id", "narrative_id");

-- AddForeignKey
ALTER TABLE "Board" ADD CONSTRAINT "Board_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User"("user_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Video" ADD CONSTRAINT "Video_board_id_fkey" FOREIGN KEY ("board_id") REFERENCES "Board"("board_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Video" ADD CONSTRAINT "Video_channel_id_fkey" FOREIGN KEY ("channel_id") REFERENCES "Channel"("channel_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Claim" ADD CONSTRAINT "Claim_video_id_fkey" FOREIGN KEY ("video_id") REFERENCES "Video"("video_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Claim" ADD CONSTRAINT "Claim_narrative_id_fkey" FOREIGN KEY ("narrative_id") REFERENCES "Narrative"("narrative_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Narrative" ADD CONSTRAINT "Narrative_board_id_fkey" FOREIGN KEY ("board_id") REFERENCES "Board"("board_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Trend" ADD CONSTRAINT "Trend_board_id_fkey" FOREIGN KEY ("board_id") REFERENCES "Board"("board_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TrendData" ADD CONSTRAINT "TrendData_trend_id_fkey" FOREIGN KEY ("trend_id") REFERENCES "Trend"("trend_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TrendData" ADD CONSTRAINT "TrendData_narrative_id_fkey" FOREIGN KEY ("narrative_id") REFERENCES "Narrative"("narrative_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "BoardChannel" ADD CONSTRAINT "BoardChannel_board_id_fkey" FOREIGN KEY ("board_id") REFERENCES "Board"("board_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "BoardChannel" ADD CONSTRAINT "BoardChannel_channel_id_fkey" FOREIGN KEY ("channel_id") REFERENCES "Channel"("channel_id") ON DELETE RESTRICT ON UPDATE CASCADE;
