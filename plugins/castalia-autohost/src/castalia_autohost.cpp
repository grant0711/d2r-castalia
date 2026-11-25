// Castalia Auto-Host & In-Game Host/Join Guide Plugin (D2RLoader PluginSDK ABI 4, MIT)
// - Reads mods/castalia/d2rloader/config/castalia_launch_intent.json written by Castalia Launcher.
// - On D2RLoader 1.3.2+ (WidgetService setters): auto-fills D2RLoaderMultiplayerPanel fields.
// - On D2RLoader 1.3.1-beta: opens a clean in-game Castalia Host/Join Guide panel right inside
//   fullscreen D2R when Multiplayer opens so players never have to alt-tab to see instructions.

#include <D2RLPlugin/api.h>

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

namespace {

static constexpr D2RL::PluginInfo PluginMetadata {
	.infoSize    = D2RL::PluginInfoSize,
	.abiVersion  = D2RL_PLUGIN_ABI_VERSION,
	.id          = "castalia-autohost",
	.name        = "Castalia Auto-Host",
	.version     = "0.2.0",
	.author      = "Castalia",
	.description = "In-game Castalia Host/Join Guide & auto-fill for D2RLoaderMultiplayerPanel.",
	.flags       = D2RL::PluginFlags::Client,
};

struct LaunchIntent {
	bool        loaded           = false;
	std::string mode;            // "host" | "join"
	std::string gameName;
	std::string description;
	std::string password;
	int         difficulty       = 0; // 0=Normal, 1=Nightmare, 2=Hell
	bool        unlisted         = true;
	bool        lanOnly          = false;
	int         maxPlayers       = 5;
	bool        levelDiffEnabled = false;
	std::string gameId;
	int         gamePort         = 4000;
};

static const D2RL::PluginContext*   gCtx       = nullptr;
static const D2RL::WidgetService*   gWidgets   = nullptr;
static const D2RL::ThreadService*   gThreads   = nullptr;
static const D2RL::PanelService*    gPanels    = nullptr;
static const D2RL::ResourceService* gResources = nullptr;

static D2RL::Panels::RegistrationHandle    gGuidePanel    = D2RL::Panels::InvalidHandle;
static D2RL::Resources::RegistrationHandle gGuideResource = D2RL::Resources::InvalidHandle;
static std::string                         gGuideJson;

static LaunchIntent      gIntent {};
static std::atomic<bool> gRunning    { false };
static std::atomic<bool> gApplied    { false };
static std::atomic<bool> gGuideShown { false };
static std::thread       gWatcher;

static auto EscapeJson(const std::string& s) -> std::string {
	std::string out;
	out.reserve(s.size() + 8);
	for (char c : s) {
		if (c == '"' || c == '\\') out.push_back('\\');
		else if (c == '\n') { out += "\\n"; continue; }
		else if (c == '\r') continue;
		out.push_back(c);
	}
	return out;
}

static auto ExtractJsonString(const std::string& json, const char* key) -> std::string {
	const std::string needle = std::string("\"") + key + "\"";
	auto pos = json.find(needle);
	if (pos == std::string::npos) return {};
	pos = json.find(':', pos + needle.size());
	if (pos == std::string::npos) return {};
	pos = json.find('"', pos + 1);
	if (pos == std::string::npos) return {};
	++pos;
	std::string out;
	while (pos < json.size() && json[pos] != '"') {
		if (json[pos] == '\\' && pos + 1 < json.size()) ++pos;
		out.push_back(json[pos++]);
	}
	return out;
}

static auto ExtractJsonInt(const std::string& json, const char* key, int fallback) -> int {
	const std::string needle = std::string("\"") + key + "\"";
	auto pos = json.find(needle);
	if (pos == std::string::npos) return fallback;
	pos = json.find(':', pos + needle.size());
	if (pos == std::string::npos) return fallback;
	++pos;
	while (pos < json.size() && (json[pos] == ' ' || json[pos] == '\t')) ++pos;
	try { return std::stoi(json.substr(pos)); } catch (...) { return fallback; }
}

static auto ExtractJsonBool(const std::string& json, const char* key, bool fallback) -> bool {
	const std::string needle = std::string("\"") + key + "\"";
	auto pos = json.find(needle);
	if (pos == std::string::npos) return fallback;
	pos = json.find(':', pos + needle.size());
	if (pos == std::string::npos) return fallback;
	++pos;
	while (pos < json.size() && (json[pos] == ' ' || json[pos] == '\t')) ++pos;
	if (json.compare(pos, 4, "true") == 0) return true;
	if (json.compare(pos, 5, "false") == 0) return false;
	return fallback;
}

static auto LoadLaunchIntent() -> LaunchIntent {
	LaunchIntent intent {};
	const char* candidates[] = {
		"mods/castalia/d2rloader/config/castalia_launch_intent.json",
		"d2rloader/config/castalia_launch_intent.json",
	};
	std::string raw;
	for (const char* path : candidates) {
		std::ifstream f(path);
		if (f.is_open()) {
			std::ostringstream ss;
			ss << f.rdbuf();
			raw = ss.str();
			break;
		}
	}
	if (raw.empty()) return intent;

	intent.loaded           = true;
	intent.mode             = ExtractJsonString(raw, "mode");
	intent.gameName         = ExtractJsonString(raw, "game_name");
	intent.description      = ExtractJsonString(raw, "description");
	intent.password         = ExtractJsonString(raw, "password");
	intent.difficulty       = ExtractJsonInt(raw, "difficulty", 0);
	intent.unlisted         = ExtractJsonBool(raw, "unlisted", true);
	intent.lanOnly          = ExtractJsonBool(raw, "lan_only", false);
	intent.maxPlayers       = ExtractJsonInt(raw, "max_players", 5);
	intent.levelDiffEnabled = ExtractJsonBool(raw, "level_diff_enabled", false);
	intent.gameId           = ExtractJsonString(raw, "game_id");
	intent.gamePort         = ExtractJsonInt(raw, "game_port", 4000);
	return intent;
}

static auto DifficultyName(int d) -> const char* {
	if (d == 1) return "Nightmare";
	if (d == 2) return "Hell";
	return "Normal";
}

static auto BuildGuidePanelJson(const LaunchIntent& intent) -> std::string {
	std::string heading;
	std::string body;
	if (intent.mode == "host") {
		heading = "CASTALIA HOST GUIDE";
		body =
			"1. Uncheck 'LAN Only' (keep 'Unlisted' checked)\n"
			"2. Click Game Name -> Ctrl+V:  " + intent.gameName + "\n"
			"3. Difficulty: " + std::string(DifficultyName(intent.difficulty)) +
			"   |   Max Players: " + std::to_string(intent.maxPlayers) + "\n"
			"4. Leave Password & Level Diff blank -> Create Game\n"
			"(Press ESC to dismiss this guide)";
	} else {
		heading = "CASTALIA JOIN GUIDE";
		const std::string addr = intent.gameId.empty() ? "(check Launcher)" : intent.gameId;
		const std::string portNote = (intent.gamePort > 0 && intent.gamePort != 4000)
			? ("   (Port " + std::to_string(intent.gamePort) + " auto-configured!)\n")
			: "\n";
		body =
			"1. Click the 'Direct Join' tab at the top of Multiplayer\n"
			"2. Click the IP / Host Address box -> Press Ctrl+V:\n"
			"   " + addr + portNote +
			"3. Leave Password blank (unless Host set one) -> Click Join Game\n"
			"(Press ESC to dismiss this guide)";
	}

	std::ostringstream ss;
	ss << R"json({
	"type": "Panel", "name": "castalia-autohost/HostGuidePanel",
	"fields": {
		"anchor": { "x": 1.0, "y": 0.5 },
		"priority": 999999
	},
	"children": [
		{
			"type": "ImageWidget", "name": "Frame",
			"fields": {
				"rect": { "x": -1160, "y": -260 },
				"filename": "Panel\\Modals\\Modal_No_Title_BG"
			},
			"children": [
				{
					"type": "TextBoxWidget", "name": "Heading",
					"fields": {
						"rect": { "x": 65, "y": 42, "width": 920, "height": 54 },
						"text": ")json" << EscapeJson(heading) << R"json(",
						"style": "$StyleSettingsTitle"
					}
				},
				{
					"type": "ButtonWidget", "name": "CloseBtn",
					"fields": {
						"rect": { "x": 1030, "y": 28 },
						"filename": "PANEL\\closebtn_4x",
						"hoveredFrame": 3,
						"onClickMessage": "PanelManager:ClosePanel:castalia-autohost/HostGuidePanel"
					}
				},
				{
					"type": "TextBoxWidget", "name": "Steps",
					"fields": {
						"rect": { "x": 65, "y": 110, "width": 1020, "height": 340 },
						"text": ")json" << EscapeJson(body) << R"json(",
						"style": "$StyleModalDialogDescription"
					}
				}
			]
		}
	]
})json";
	return ss.str();
}

static auto FindFirstWidget(const D2RL::PluginContext* ctx, D2RL::Widgets::WidgetHandle panel, const std::vector<const char*>& names, const char** matchedName) noexcept -> D2RL::Widgets::WidgetHandle {
	for (const char* name : names) {
		D2RL::Widgets::WidgetHandle h = D2RL::Widgets::InvalidHandle;
		if (gWidgets->findWidget(ctx, panel, name, &h) == D2RL::Widgets::Result::Success && h != D2RL::Widgets::InvalidHandle) {
			if (matchedName) *matchedName = name;
			return h;
		}
	}
	return D2RL::Widgets::InvalidHandle;
}

static void TrySetInput(const D2RL::PluginContext* ctx, D2RL::Widgets::WidgetHandle panel, const char* label, const std::vector<const char*>& names, const std::string& val) noexcept {
	if (val.empty() || !D2RL::HasWidgetServiceField(gWidgets, D2RL::WidgetServiceSetInputTextFieldEnd)) return;
	const char* hit = nullptr;
	const auto h = FindFirstWidget(ctx, panel, names, &hit);
	if (h != D2RL::Widgets::InvalidHandle) {
		const auto r = gWidgets->setInputText(ctx, h, val.c_str());
		D2RL::LogInfoF(ctx, "[castalia-autohost] SetInput %s (%s)='%s' -> %u", label, hit, val.c_str(), static_cast<unsigned>(r));
	}
}

static void TrySetToggle(const D2RL::PluginContext* ctx, D2RL::Widgets::WidgetHandle panel, const char* label, const std::vector<const char*>& names, bool state) noexcept {
	if (!D2RL::HasWidgetServiceField(gWidgets, D2RL::WidgetServiceSetToggleStateFieldEnd)) return;
	const char* hit = nullptr;
	const auto h = FindFirstWidget(ctx, panel, names, &hit);
	if (h != D2RL::Widgets::InvalidHandle) {
		const auto r = gWidgets->setToggleState(ctx, h, state);
		D2RL::LogInfoF(ctx, "[castalia-autohost] SetToggle %s (%s)=%d -> %u", label, hit, state ? 1 : 0, static_cast<unsigned>(r));
	}
}

static void TrySetDropdown(const D2RL::PluginContext* ctx, D2RL::Widgets::WidgetHandle panel, const char* label, const std::vector<const char*>& names, uint32_t idx) noexcept {
	if (!D2RL::HasWidgetServiceField(gWidgets, D2RL::WidgetServiceSetDropdownSelectionFieldEnd)) return;
	const char* hit = nullptr;
	const auto h = FindFirstWidget(ctx, panel, names, &hit);
	if (h != D2RL::Widgets::InvalidHandle) {
		const auto r = gWidgets->setDropdownSelection(ctx, h, idx);
		D2RL::LogInfoF(ctx, "[castalia-autohost] SetDropdown %s (%s)=%u -> %u", label, hit, idx, static_cast<unsigned>(r));
	}
}

static void ApplyIntentOnUiThread(const D2RL::PluginContext* ctx, void*) noexcept {
	if (ctx == nullptr || gWidgets == nullptr || !gIntent.loaded) return;

	D2RL::Widgets::WidgetHandle mpPanel = D2RL::Widgets::InvalidHandle;
	bool mpVisible = false;
	if (gWidgets->findPanel(ctx, "D2RLoaderMultiplayerPanel", &mpPanel) == D2RL::Widgets::Result::Success && mpPanel != D2RL::Widgets::InvalidHandle) {
		mpVisible = true;
		if (D2RL::HasWidgetServiceField(gWidgets, D2RL::WidgetServiceGetWidgetStateFieldEnd)) {
			D2RL::Widgets::State st {};
			if (gWidgets->getWidgetState(ctx, mpPanel, &st) == D2RL::Widgets::Result::Success) {
				mpVisible = st.visible;
			}
		}
	}

	// Auto-close the guide panel as soon as Multiplayer closes or player enters game
	if (!mpVisible) {
		if (gGuideShown.load() && gPanels != nullptr && gGuidePanel != D2RL::Panels::InvalidHandle) {
			gPanels->closePanel(ctx, gGuidePanel);
			gGuideShown.store(false);
		}
		return;
	}

	if (gApplied.load()) return;

	const bool canAutoFill = D2RL::HasWidgetServiceField(gWidgets, D2RL::WidgetServiceSetInputTextFieldEnd);
	D2RL::LogInfoF(ctx, "[castalia-autohost] D2RLoaderMultiplayerPanel open! mode='%s' canAutoFill=%d serviceSize=%u",
		gIntent.mode.c_str(), canAutoFill ? 1 : 0, gWidgets->serviceSize);

	if (canAutoFill) {
		if (gIntent.mode == "host") {
			TrySetToggle(ctx, mpPanel, "LanOnly", { "LanOnly", "LanOnlyToggle", "LanOnlyCheckbox", "LocalOnly" }, gIntent.lanOnly);
			TrySetToggle(ctx, mpPanel, "Unlisted", { "Unlisted", "UnlistedToggle", "UnlistedCheckbox", "UnlistedGame" }, gIntent.unlisted);
			TrySetInput(ctx, mpPanel, "GameName", { "GameName", "GameNameInput", "GameNameTextBox" }, gIntent.gameName);
			TrySetInput(ctx, mpPanel, "Description", { "GameDescription", "Description", "DescriptionInput" }, gIntent.description);
			TrySetInput(ctx, mpPanel, "Password", { "GamePassword", "Password", "PasswordInput" }, gIntent.password);
			TrySetInput(ctx, mpPanel, "MaxPlayers", { "MaxPlayers", "MaxPlayersInput", "PlayerCount" }, std::to_string(gIntent.maxPlayers));
			TrySetDropdown(ctx, mpPanel, "Difficulty", { "Difficulty", "DifficultyDropdown", "HostDifficulty" }, static_cast<uint32_t>(gIntent.difficulty < 0 ? 0 : gIntent.difficulty));
			TrySetToggle(ctx, mpPanel, "LevelDiff", { "LevelDifference", "LevelDiffToggle", "MaxLevelDiff" }, gIntent.levelDiffEnabled);
		} else if (gIntent.mode == "join") {
			TrySetInput(ctx, mpPanel, "GameId", { "GameId", "GameIdInput", "DirectJoinInput", "JoinGameId" }, gIntent.gameId);
		}
	} else if (gPanels != nullptr && gGuidePanel != D2RL::Panels::InvalidHandle) {
		const auto r = gPanels->openPanel(ctx, gGuidePanel);
		if (r == D2RL::Panels::Result::Success) gGuideShown.store(true);
		D2RL::LogInfoF(ctx, "[castalia-autohost] Opened in-game Host/Join Guide panel -> %u", static_cast<unsigned>(r));
	}

	gApplied.store(true);
}

static auto CmdToggleGuide(D2R::Game::Client*, const D2RL::ConsoleCommandContext* cmd, void*) noexcept -> D2RL::ConsoleCommandResult {
	if (cmd == nullptr || cmd->plugin == nullptr || gPanels == nullptr || gGuidePanel == D2RL::Panels::InvalidHandle) {
		return D2RL::ConsoleCommandResult::Failed;
	}
	return gPanels->togglePanel(cmd->plugin, gGuidePanel) == D2RL::Panels::Result::Success
		? D2RL::ConsoleCommandResult::Handled
		: D2RL::ConsoleCommandResult::Failed;
}

static void WatcherLoop() {
	while (gRunning.load()) {
		std::this_thread::sleep_for(std::chrono::milliseconds(400));
		if (gRunning.load() && gCtx != nullptr && gThreads != nullptr && gIntent.loaded && (!gApplied.load() || gGuideShown.load())) {
			gThreads->runOnUiThread(gCtx, ApplyIntentOnUiThread, nullptr);
		}
	}
}

} // namespace

D2RL_PLUGIN_EXPORT auto D2RLoaderGetPluginInfo() noexcept -> const D2RL::PluginInfo* {
	return &PluginMetadata;
}

D2RL_PLUGIN_EXPORT auto D2RLoaderLoadPlugin(const D2RL::PluginContext* context) noexcept -> bool {
	if (context == nullptr) return false;
	gCtx = context;

	if (context->QueryService(&gWidgets) != D2RL::ServiceQueryResult::Success ||
		!D2RL::HasWidgetServiceField(gWidgets, D2RL::WidgetServiceRequiredSize)) {
		context->LogError("[castalia-autohost] WidgetService unavailable.");
		return false;
	}
	if (context->QueryService(&gThreads) != D2RL::ServiceQueryResult::Success ||
		!D2RL::HasThreadServiceField(gThreads, D2RL::ThreadServiceRequiredSize)) {
		context->LogError("[castalia-autohost] ThreadService unavailable.");
		return false;
	}

	gIntent = LoadLaunchIntent();
	if (!gIntent.loaded) {
		context->LogInfo("[castalia-autohost] Loaded (no castalia_launch_intent.json present).");
		return true;
	}

	// Register in-game Host/Join Guide panel (works on D2RLoader 1.3.1-beta immediately!)
	if (context->QueryService(&gResources) == D2RL::ServiceQueryResult::Success &&
		D2RL::HasResourceServiceField(gResources, D2RL::ResourceServiceRequiredSize) &&
		context->QueryService(&gPanels) == D2RL::ServiceQueryResult::Success &&
		D2RL::HasPanelServiceField(gPanels, D2RL::PanelServiceRequiredSize)) {
		gGuideJson = BuildGuidePanelJson(gIntent);
		const D2RL::Resources::ResourceRegistration res {
			.structSize = D2RL::Resources::ResourceRegistrationSize,
			.path       = "data/global/ui/layouts/castalia-autohost/HostGuidePanelhd.json",
			.bytes      = gGuideJson.data(),
			.byteCount  = gGuideJson.size(),
		};
		if (gResources->registerResource(context, &res, &gGuideResource) == D2RL::Resources::Result::Success) {
			const D2RL::Panels::PanelRegistration reg {
				.structSize = D2RL::Panels::PanelRegistrationSize,
				.flags      = D2RL::Panels::PanelFlags::CloseOnEscape,
				.localId    = "HostGuidePanel",
			};
			if (gPanels->registerPanel(context, &reg, &gGuidePanel) == D2RL::Panels::Result::Success) {
				context->RegisterConsoleCommand("castalia_guide", CmdToggleGuide, "Toggle the in-game Castalia Host/Join Guide panel.");
				context->LogInfo("[castalia-autohost] Registered in-game HostGuidePanel.");
			}
		}
	}

	D2RL::LogInfoF(context, "[castalia-autohost] Loaded launch intent: mode=%s game='%s' diff=%d max=%d",
		gIntent.mode.c_str(), gIntent.gameName.c_str(), gIntent.difficulty, gIntent.maxPlayers);
	gApplied.store(false);
	gRunning.store(true);
	gWatcher = std::thread(WatcherLoop);
	return true;
}

D2RL_PLUGIN_EXPORT void D2RLoaderUnloadPlugin() noexcept {
	gRunning.store(false);
	if (gWatcher.joinable()) gWatcher.join();
	gCtx       = nullptr;
	gWidgets   = nullptr;
	gThreads   = nullptr;
	gPanels    = nullptr;
	gResources = nullptr;
	gGuidePanel    = D2RL::Panels::InvalidHandle;
	gGuideResource = D2RL::Resources::InvalidHandle;
}
