// Test if core imports work
import { TELEGRAM_TOKEN, WORKING_DIR } from "./src/config";
import { Bot } from "grammy";

console.log("✅ Core imports successful");
console.log("Working dir:", WORKING_DIR);
console.log("Has token:", !!TELEGRAM_TOKEN);
