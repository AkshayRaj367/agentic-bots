const { Client, GatewayIntentBits } = require('discord.js');
const axios = require('axios');

const WEBHOOK_URL = process.env.WEBHOOK_URL;
const BOT_TOKEN = process.env.BOT_TOKEN;

console.log('Token loaded:', BOT_TOKEN ? 'YES ✅' : 'NO ❌');
console.log('Webhook loaded:', WEBHOOK_URL ? 'YES ✅' : 'NO ❌');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
});

client.on('ready', () => {
  console.log(`✅ Bot is online as ${client.user.tag}`);
});

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  if (!message.content.startsWith('!review')) return;

  const code = message.content.replace('!review', '').trim();

  if (!code) {
    message.reply('Please send code after !review');
    return;
  }

  await message.reply('⏳ Analyzing your code...');

  try {
    await axios.post(WEBHOOK_URL, { content: code });
  } catch (error) {
    console.error('Webhook error:', error.message);
    message.reply('❌ Error connecting to n8n!');
  }
});

// Keep Render alive
const http = require('http');
http.createServer((req, res) => {
  res.write('Bot is running!');
  res.end();
}).listen(process.env.PORT || 3000);

// Ping every 10 minutes
const https = require('https');
setInterval(() => {
  https.get('https://agentic-bots.onrender.com');
  console.log('✅ Ping sent');
}, 600000);

client.login(BOT_TOKEN).catch(err => {
  console.error('❌ Login failed:', err.message);
});