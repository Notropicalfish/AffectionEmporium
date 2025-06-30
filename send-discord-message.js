// This is a serverless function, for example, at /api/send-discord-message.js
// You would deploy this on a platform like Vercel or Netlify.

// You need to install discord.js: npm install discord.js
const { Client, GatewayIntentBits } = require('discord.js');

// --- CONFIGURATION ---
// IMPORTANT: Store your bot token and server ID as secure environment variables.
// DO NOT write them directly in the code.
const BOT_TOKEN = process.env.DISCORD_BOT_TOKEN;
const GUILD_ID = process.env.DISCORD_GUILD_ID;

// Initialize the Discord client with necessary intents
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMembers, // This intent is crucial for finding users by name
    ],
});

// A flag to ensure we only log in once per server instance
let isLoggedIn = false;
if (BOT_TOKEN && !client.readyAt) { // Check if the bot is already logged in
    client.login(BOT_TOKEN).then(() => {
        isLoggedIn = true;
        console.log('Discord bot logged in successfully.');
    }).catch(err => {
        console.error("Bot login error:", err);
        isLoggedIn = false;
    });
}

// This is the main function that will be executed when the API endpoint is called
module.exports = async (req, res) => {
    // 1. Basic validation and security checks
    if (req.method !== 'POST') {
        return res.status(405).json({ message: 'Method Not Allowed' });
    }
    if (!BOT_TOKEN || !GUILD_ID) {
        console.error('Bot token or Guild ID is not configured on the server.');
        return res.status(500).json({ message: 'Server configuration error.' });
    }
    if (!isLoggedIn) {
        console.error('Bot is not logged in. Please check token and server status.');
        return res.status(500).json({ message: 'Bot is currently offline.' });
    }

    const { discordUsername, cart } = req.body;

    if (!discordUsername || !cart || cart.length === 0) {
        return res.status(400).json({ message: 'Missing Discord username or cart items.' });
    }

    try {
        // 2. Find the Discord User in the specified server
        const guild = await client.guilds.fetch(GUILD_ID);
        // Fetch all members to ensure the cache is up to date
        await guild.members.fetch(); 
        
        const member = guild.members.cache.find(m => m.user.tag === discordUsername);

        if (!member) {
            return res.status(404).json({ message: `User "${discordUsername}" not found in the server. Please check spelling and make sure they are a member.` });
        }

        // 3. Construct and send the Direct Message
        const messages = cart.map(item => item.message || `Thank you for purchasing ${item.name}!`);
        const fullMessage = "Hello from the Affection Emporium!\n\n" + messages.join('\n');

        await member.send(fullMessage);

        // 4. Send success response back to the website
        return res.status(200).json({ message: 'Successfully sent DM!' });

    } catch (error) {
        console.error('Error processing Discord request:', error);
        
        // Check for specific Discord errors to give the user better feedback
        if (error.code === 50007) { // "Cannot send messages to this user"
             return res.status(400).json({ message: 'Cannot send message. User may have DMs disabled or has blocked the bot.' });
        }
        return res.status(500).json({ message: 'An internal server error occurred while contacting the bot.' });
    }
};
