<<<<<<< HEAD
# Dograh AI

**The open-source, self-hostable alternative to Vapi & Retell** — build production voice agents with a drag-and-drop workflow builder. From zero to a working bot in under 2 minutes.

<p align="center">
  <a href="https://app.dograh.com">
    <img src="https://img.shields.io/badge/▶_Try_the_Cloud-app.dograh.com-2563eb?style=for-the-badge" alt="Try the Cloud">
  </a>
  &nbsp;
  <a href="#-get-started">
    <img src="https://img.shields.io/badge/⚡_Self--host_in_60s-One_command-111827?style=for-the-badge" alt="Self-host in 60s">
  </a>
  &nbsp;
  <a href="https://join.slack.com/t/dograh-community/shared_invite/zt-3czr47sw5-MSg1J0kJ7IMPOCHF~03auQ">
    <img src="https://img.shields.io/badge/💬_Join_Slack-Community-4A154B?style=for-the-badge&logo=slack" alt="Join Slack">
  </a>
</p>

<p align="center">
  <a href="https://docs.dograh.com">📖 Docs</a> &nbsp;·&nbsp;
  <a href="LICENSE">📜 BSD 2-Clause</a> &nbsp;·&nbsp;
  <a href="README.zh-CN.md">🌐 中文</a>
</p>

<p align="center">
  <img src="docs/images/hero.gif" alt="Dograh in action — build a workflow, launch a voice agent, talk to it" width="80%">
</p>

- **100% open source**, self-hostable — no vendor lock-in, unlike Vapi or Retell
- **Full control & transparency** — every line of code is open, with flexible LLM / TTS / STT integration
- **Maintained by YC alumni and exit founders**, committed to keeping voice AI open

## 🎥 Featured

<div align="center">
  <a href="https://www.youtube.com/watch?v=xD9JEvfCH9k">
    <img src="https://img.youtube.com/vi/xD9JEvfCH9k/maxresdefault.jpg" alt="Dograh featured by Better Stack" width="80%" style="border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
  </a>
  <br>
  <em>Featured by <strong>Better Stack</strong> — a hands-on look at Dograh</em>
</div>

<details>
<summary>📺 Prefer a 2-minute product walkthrough? Click here.</summary>

<div align="center">
  <a href="https://youtu.be/9gPneyf9M9w">
    <img src="docs/images/video_thumbnail_1.png" alt="Watch Dograh AI Demo Video" width="70%" style="border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
  </a>
</div>

</details>

## ⚖️ Dograh vs Vapi vs Retell

An honest comparison on the axes that matter most to teams evaluating voice AI platforms.

|  | **Dograh** | **Vapi** | **Retell** |
|---|---|---|---|
| **License** | BSD 2-Clause (open source) | Proprietary | Proprietary |
| **Self-hostable** | ✅ Yes — one Docker command | ❌ SaaS only | ❌ SaaS only |
| **Pricing** | Free (self-host) · usage-based (cloud) | Per-minute SaaS | Per-minute SaaS |
| **Bring your own LLM / STT / TTS** | ✅ Any provider, or use Dograh's stack | Configurable within their integrations | Configurable within their integrations |
| **Source-level customization** | ✅ Every line is yours to modify | ❌ Closed source | ❌ Closed source |
| **Data residency** | Your infra, your rules | Their cloud | Their cloud |
| **Vendor lock-in** | None | Full | Full |


## 🚀 Get Started

##### Download and setup Dograh on your Local Machine

> **Note**
> We collect anonymous usage data to improve the product. You can opt out by setting the `ENABLE_TELEMETRY` to `false` in the below command.

> **Note**
> If you wish to run the platform on a remote server instead, checkout our [Documentation](https://docs.dograh.com/deployment/docker#option-2:-remote-server-deployment)

```bash
curl -o docker-compose.yaml https://raw.githubusercontent.com/dograh-hq/dograh/main/docker-compose.yaml && REGISTRY=ghcr.io/dograh-hq ENABLE_TELEMETRY=true docker compose up --pull always
```

> **Note**
> First startup may take 2-3 minutes to download all images. Once running, open http://localhost:3010 to create your first AI voice assistant!
> For common issues and solutions, see 🔧 **[Troubleshooting](docs/troubleshooting.md)**.

### 🎙️ Your First Voice Bot

1. Open [http://localhost:3010](http://localhost:3010) in your browser.
2. Pick **Inbound** or **Outbound**, name your bot (e.g. _Lead Qualification_), and describe the use case in 5–10 words (e.g. _Screen insurance form submissions for purchase intent_).
3. Click **Web Call** — you're talking to your bot.

> 🔑 **No API keys needed.** Dograh ships with auto-generated keys and its own LLM / TTS / STT stack. Connect your own keys for LLM, TTS, STT, or Telephony (e.g. Twilio, Vonage, Telnyx) anytime.

## Features

### Voice Capabilities

- Telephony: Built-in telephony integration like Twilio, Vonage, Vobiz, Cloudonix (easily add others), with support for transferring calls to human agents
- Languages: English support (expandable to other languages)
- Custom Models: Bring your own TTS/STT models
- Real-time Processing: Low-latency voice interactions

### Developer Experience

- Zero Config Start: Auto-generated API keys for instant testing
- Python-Based: Built on Python for easy customization
- Docker-First: Containerized for consistent deployments
- Modular Architecture: Swap components as needed

### Testing & Quality

- **Test Mode**: Try your agent end-to-end before publishing, with no production calls or data affected
- **In-Dashboard Web Calls**: Talk to your bot directly while building — no telephony setup required
- **QA Node**: A built-in workflow node that analyzes prompt quality across your other nodes

## Deployment Options

### Local Development

Refer [Local Setup](https://docs.dograh.com/contribution/setup)

### Self-Hosted Deployment

For detailed deployment instructions including remote server setup with HTTPS, see our [Docker Deployment Guide](https://docs.dograh.com/deployment/docker).

### Cloud Version

Visit [https://www.dograh.com](https://www.dograh.com/) for our managed cloud offering.

## 📚Documentation

You can go to [https://docs.dograh.com](https://docs.dograh.com/) for our documentation.

## 📦 SDKs

- **Python SDK** — [pypi.org/project/dograh-sdk](https://pypi.org/project/dograh-sdk/)
- **Node SDK** — [npmjs.com/package/@dograh/sdk](https://www.npmjs.com/package/@dograh/sdk)

## 🤝Community & Support

> 👋 **Coming from the Better Stack video?** Drop your use case in our [pinned GitHub Discussion](https://github.com/orgs/dograh-hq/discussions/291) — we read every reply and the founders personally onboard early adopters.

- **Slack** — the cornerstone of Dograh AI contributions. Connect with maintainers, discuss features before coding, get help with setup, and stay current on contribution sprints.
- **GitHub Discussions** — share use cases, ask questions, swap workflow recipes.
- **GitHub Issues** — report bugs or request features.

👉 Join us → [Dograh Community Slack](https://join.slack.com/t/dograh-community/shared_invite/zt-3czr47sw5-MSg1J0kJ7IMPOCHF~03auQ)

## 🙌 Contributing

We love contributions! Dograh AI is 100% open source and we intend to keep it that way.

### Getting Started

- Fork the repository
- Create your feature branch (git checkout -b feature/AmazingFeature)
- Commit your changes (git commit -m 'Add some AmazingFeature')
- Push to the branch (git push origin feature/AmazingFeature)
- Open a Pull Request

## ⭐ Star History

<a href="https://star-history.com/#dograh-hq/dograh&Date">
  <img src="https://api.star-history.com/svg?repos=dograh-hq/dograh&type=Date" alt="Dograh star history" width="80%">
</a>

## 📄 License

Dograh AI is licensed under the [BSD 2-Clause License](LICENSE)- the same license as projects that were used in building Dograh AI, ensuring compatibility and freedom to use, modify, and distribute.

## 🏢 About

Built with ❤️ by **Dograh** (Zansat Technologies Private Limited)
Founded by YC alumni and exit founders committed to keeping voice AI open and accessible to everyone.

<br><br><br>

  <p align="center">
    <a href="https://github.com/dograh-hq/dograh/stargazers">⭐ Star us on GitHub</a> |
    <a href="https://app.dograh.com">☁️ Try Cloud Version</a> |
    <a href="https://join.slack.com/t/dograh-community/shared_invite/zt-3czr47sw5-MSg1J0kJ7IMPOCHF~03auQ">💬 Join Slack</a>
  </p>
=======
# CallAgen



## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

* [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
* [Add files using the command line](https://docs.gitlab.com/topics/git/add_files/#add-files-to-a-git-repository) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://gitlab.beeline.uz/knowledge-agent/bee-call/callagen.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

* [Set up project integrations](https://gitlab.beeline.uz/knowledge-agent/bee-call/callagen/-/settings/integrations)

## Collaborate with your team

* [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
* [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
* [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
* [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
* [Set auto-merge](https://docs.gitlab.com/user/project/merge_requests/auto_merge/)

## Test and Deploy

Use the built-in continuous integration in GitLab.

* [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/)
* [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
* [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
* [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
* [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
>>>>>>> c52b1993d003fbde318d431f6419e3e2224c2c9f
