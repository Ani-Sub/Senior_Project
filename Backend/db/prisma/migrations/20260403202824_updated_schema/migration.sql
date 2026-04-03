/*
  Warnings:

  - The primary key for the `Board` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - You are about to drop the column `processed_at` on the `Board` table. All the data in the column will be lost.
  - The primary key for the `BoardChannel` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - You are about to drop the column `channel_title` on the `Channel` table. All the data in the column will be lost.
  - The primary key for the `Claim` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - The primary key for the `User` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - You are about to drop the `Keyword` table. If the table is not empty, all the data it contains will be lost.
  - A unique constraint covering the columns `[email]` on the table `User` will be added. If there are existing duplicate values, this will fail.
  - Changed the type of `board_id` on the `Board` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.
  - Changed the type of `user_id` on the `Board` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.
  - Changed the type of `board_id` on the `BoardChannel` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.
  - Added the required column `accuracy_rate` to the `Channel` table without a default value. This is not possible if the table is not empty.
  - Added the required column `channel_name` to the `Channel` table without a default value. This is not possible if the table is not empty.
  - Added the required column `flagged_claims` to the `Channel` table without a default value. This is not possible if the table is not empty.
  - Added the required column `last_assessed_at` to the `Channel` table without a default value. This is not possible if the table is not empty.
  - Added the required column `risk_level` to the `Channel` table without a default value. This is not possible if the table is not empty.
  - Added the required column `risk_score` to the `Channel` table without a default value. This is not possible if the table is not empty.
  - Added the required column `total_claims` to the `Channel` table without a default value. This is not possible if the table is not empty.
  - Added the required column `claim_type` to the `Claim` table without a default value. This is not possible if the table is not empty.
  - Added the required column `confidence_score` to the `Claim` table without a default value. This is not possible if the table is not empty.
  - Added the required column `is_verified` to the `Claim` table without a default value. This is not possible if the table is not empty.
  - Added the required column `risk_level` to the `Claim` table without a default value. This is not possible if the table is not empty.
  - Changed the type of `claim_id` on the `Claim` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.
  - Made the column `processed_at` on table `Claim` required. This step will fail if there are existing NULL values in that column.
  - Added the required column `color` to the `Narrative` table without a default value. This is not possible if the table is not empty.
  - Changed the type of `board_id` on the `Narrative` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.
  - Made the column `first_seen_at` on table `Narrative` required. This step will fail if there are existing NULL values in that column.
  - Made the column `last_seen_at` on table `Narrative` required. This step will fail if there are existing NULL values in that column.
  - Added the required column `initials` to the `User` table without a default value. This is not possible if the table is not empty.
  - Added the required column `role` to the `User` table without a default value. This is not possible if the table is not empty.
  - Changed the type of `user_id` on the `User` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.
  - Changed the type of `board_id` on the `Video` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.

*/
-- CreateEnum
CREATE TYPE "Plan" AS ENUM ('free', 'analyst', 'enterprise');

-- CreateEnum
CREATE TYPE "Layout" AS ENUM ('overview', 'trends', 'claims');

-- CreateEnum
CREATE TYPE "RiskLevel" AS ENUM ('low', 'medium', 'high');

-- CreateEnum
CREATE TYPE "ClaimType" AS ENUM ('factual', 'opinion');

-- DropForeignKey
ALTER TABLE "Board" DROP CONSTRAINT "Board_user_id_fkey";

-- DropForeignKey
ALTER TABLE "BoardChannel" DROP CONSTRAINT "BoardChannel_board_id_fkey";

-- DropForeignKey
ALTER TABLE "Claim" DROP CONSTRAINT "Claim_video_id_fkey";

-- DropForeignKey
ALTER TABLE "Keyword" DROP CONSTRAINT "Keyword_board_id_fkey";

-- DropForeignKey
ALTER TABLE "Narrative" DROP CONSTRAINT "Narrative_board_id_fkey";

-- DropForeignKey
ALTER TABLE "Video" DROP CONSTRAINT "Video_board_id_fkey";

-- AlterTable
ALTER TABLE "Board" DROP CONSTRAINT "Board_pkey",
DROP COLUMN "processed_at",
ADD COLUMN     "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN     "layout" "Layout" NOT NULL DEFAULT 'overview',
ADD COLUMN     "search_terms" TEXT[],
DROP COLUMN "board_id",
ADD COLUMN     "board_id" UUID NOT NULL,
DROP COLUMN "user_id",
ADD COLUMN     "user_id" UUID NOT NULL,
ALTER COLUMN "board_name" SET DATA TYPE VARCHAR(500),
ADD CONSTRAINT "Board_pkey" PRIMARY KEY ("board_id");

-- AlterTable
ALTER TABLE "BoardChannel" DROP CONSTRAINT "BoardChannel_pkey",
DROP COLUMN "board_id",
ADD COLUMN     "board_id" UUID NOT NULL,
ADD CONSTRAINT "BoardChannel_pkey" PRIMARY KEY ("board_id", "channel_id");

-- AlterTable
ALTER TABLE "Channel" DROP COLUMN "channel_title",
ADD COLUMN     "accuracy_rate" DOUBLE PRECISION NOT NULL,
ADD COLUMN     "channel_name" VARCHAR(500) NOT NULL,
ADD COLUMN     "flagged_claims" INTEGER NOT NULL,
ADD COLUMN     "last_assessed_at" TIMESTAMP(3) NOT NULL,
ADD COLUMN     "risk_level" "RiskLevel" NOT NULL,
ADD COLUMN     "risk_score" DOUBLE PRECISION NOT NULL,
ADD COLUMN     "total_claims" INTEGER NOT NULL;

-- AlterTable
ALTER TABLE "Claim" DROP CONSTRAINT "Claim_pkey",
ADD COLUMN     "accuracy_rating" DOUBLE PRECISION,
ADD COLUMN     "claim_type" "ClaimType" NOT NULL,
ADD COLUMN     "confidence_score" DOUBLE PRECISION NOT NULL,
ADD COLUMN     "is_verified" BOOLEAN NOT NULL,
ADD COLUMN     "risk_level" "RiskLevel" NOT NULL,
DROP COLUMN "claim_id",
ADD COLUMN     "claim_id" UUID NOT NULL,
ALTER COLUMN "video_id" SET DATA TYPE TEXT,
ALTER COLUMN "processed_at" SET NOT NULL,
ALTER COLUMN "processed_at" SET DEFAULT CURRENT_TIMESTAMP,
ADD CONSTRAINT "Claim_pkey" PRIMARY KEY ("claim_id");

-- AlterTable
ALTER TABLE "Narrative" ADD COLUMN     "color" TEXT NOT NULL,
DROP COLUMN "board_id",
ADD COLUMN     "board_id" UUID NOT NULL,
ALTER COLUMN "first_seen_at" SET NOT NULL,
ALTER COLUMN "first_seen_at" SET DEFAULT CURRENT_TIMESTAMP,
ALTER COLUMN "last_seen_at" SET NOT NULL;

-- AlterTable
ALTER TABLE "User" DROP CONSTRAINT "User_pkey",
ADD COLUMN     "initials" TEXT NOT NULL,
ADD COLUMN     "plan" "Plan" NOT NULL DEFAULT 'free',
ADD COLUMN     "role" TEXT NOT NULL,
DROP COLUMN "user_id",
ADD COLUMN     "user_id" UUID NOT NULL,
ADD CONSTRAINT "User_pkey" PRIMARY KEY ("user_id");

-- AlterTable
ALTER TABLE "Video" DROP COLUMN "board_id",
ADD COLUMN     "board_id" UUID NOT NULL;

-- DropTable
DROP TABLE "Keyword";

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- AddForeignKey
ALTER TABLE "Board" ADD CONSTRAINT "Board_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User"("user_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Video" ADD CONSTRAINT "Video_board_id_fkey" FOREIGN KEY ("board_id") REFERENCES "Board"("board_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Claim" ADD CONSTRAINT "Claim_video_id_fkey" FOREIGN KEY ("video_id") REFERENCES "Video"("video_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Narrative" ADD CONSTRAINT "Narrative_board_id_fkey" FOREIGN KEY ("board_id") REFERENCES "Board"("board_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "BoardChannel" ADD CONSTRAINT "BoardChannel_board_id_fkey" FOREIGN KEY ("board_id") REFERENCES "Board"("board_id") ON DELETE RESTRICT ON UPDATE CASCADE;
