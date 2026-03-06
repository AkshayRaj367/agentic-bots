require('dotenv').config();
const { Client, GatewayIntentBits } = require('discord.js');
const axios = require('axios');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
});

const WEBHOOK_URL = process.env.WEBHOOK_URL;
const BOT_TOKEN = process.env.BOT_TOKEN;

client.on('ready', () => {
  console.log(`✅ Bot is online as ${client.user.tag}`);
});

client.on('messageCreate', async (message) => {
  // Ignore bot messages to prevent infinite loop
  if (message.author.bot) return;
  
  // Only trigger when message starts with !review
  if (!message.content.startsWith('!review')) return;

  const code = message.content.replace('!review', '').trim();
  
  if (!code) {
    message.reply('Please send code after !review\nExample: `!review print("hello")`');
    return;
  }

  await message.reply('⏳ Analyzing your code...');

  try {
    await axios.post(WEBHOOK_URL, { content: code });
  } catch (error) {
    message.reply('❌ Error connecting to n8n. Make sure it is running!');
  }
});

client.login(BOT_TOKEN);

