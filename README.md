# SecondBrain: Your Intelligent Bookmarking Tool

## 🌟 Highlights

* **More than bookmarks** - Saves full context of web pages, not just links
* **Natural language search** - Ask questions about your saved content
* **Intelligent retrieval** - Find information even when your query doesn't exactly match saved text
* **Browser integration** - Seamlessly save pages while browsing
* **Self-hostable** - Keep your data private and secure

## 📖 Overview

SecondBrain transforms how you save and retrieve web content. Unlike traditional bookmarking tools that only save links, SecondBrain captures the full context of web pages and makes them searchable using natural language.

Think of it as your personal research assistant: it captures what you read, remembers it for you, and helps you find it again with simple questions like "What were those articles I saved about AI ethics?"

### 🧠 Inspiration

We were frustrated by the limitations of traditional bookmarking tools—they save links but not context. Often, we'd bookmark dozens of articles only to forget why we saved them in the first place. SecondBrain was born from the idea of creating a more intelligent, question-friendly way to organize and retrieve web content.

### 👤 Authors

SecondBrain is a hackathon project created by a team of developers passionate about knowledge management and AI-enhanced productivity tools.

## 🚀 Features

- **Smart Page Capture**: Saves URLs, metadata, and full page content
- **AI-Powered Search**: Find saved content with natural language queries
- **Instant Previews**: Quickly view saved pages without leaving the extension
- **Semantic Understanding**: Returns relevant results even when query words don't match exactly
- **Clean Interface**: Intuitive UI that feels lightweight and functional

## 💻 How We Built It

SecondBrain is built as a Chrome extension + full-stack application with three main components:

### Browser Extension
- Captures page URL, metadata and contents on click
- Sends payload to our Flask API
- Provides instant search interface

### Backend (Flask)
- Processes and extracts text content from web pages
- Uses Model Context Protocol (MCP) with Anthropic's Claude for intelligent search
- Stores page data in SQLite database

### Web Interface
- Displays bookmarks and search results
- Provides detailed views of saved content
- Allows for content management and organization

Our tech stack was chosen for rapid iteration, ease of self-hosting, and efficient semantic search capabilities.

## 🔧 Installation

### Prerequisites
- Python 3.8+
- Chrome/Chromium browser
- Anthropic API key (for Claude integration)

### Server Setup
1. Clone the repository:
```
git clone https://github.com/yourusername/secondbrain.git
cd secondbrain
```

2. Install server dependencies:
```
cd server
pip install -r requirements.txt
```

3. Set up environment variables:
```
export ANTHROPIC_API_KEY=your_api_key_here
```

4. Start the server:
```
python app.py
```

### Browser Extension Setup
1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `extension` folder from this repo
4. Click the SecondBrain icon in your browser toolbar to start using it

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Anthropic Claude](https://www.anthropic.com/) for powering our semantic search
- [Model Context Protocol](https://github.com/anthropics/anthropic-tools) for enabling AI integration
- All the users who provided feedback during development
