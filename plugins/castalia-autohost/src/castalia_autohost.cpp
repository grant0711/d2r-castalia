// Castalia Auto-Host & Auto-Join Plugin (D2RLoader PluginSDK ABI 4, MIT)
// Reads mods/castalia/d2rloader/config/castalia_launch_intent.json written by the
// Castalia Launcher and pre-populates D2RLoaderMultiplayerPanel fields automatically.

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
	.version     = "0.1.0",
	.author      = "Castalia",
	.description = "Pre-populates D2RLoaderMultiplayerPanel from Castalia Launcher launch intent.",
	.flags       = D2RL::PluginFlags::None,
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
};

static const D2RL::PluginContext* gCtx     = nullptr;
static const D2RL::WidgetService* gWidgets = nullptr;
static const D2RL::ThreadService* gThreads = nullptr;

static LaunchIntent      gIntent {};
static std::atomic<bool> gRunning { false };
static std::atomic<bool> gApplied { false };
static std::thread       gWatcher;

// Minimal JSON value extractors (flat launch_intent.json, zero external deps)
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
		if (json[pos] == '\\' && pos + 1 < json.size()) {
			++pos;
		}
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
	try {
		return std::stoi(json.substr(pos));
	} catch (...) {
		return fallback;
	}
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
	return intent;
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
	if (ctx == nullptr || gWidgets == nullptr || !gIntent.loaded || gApplied.load()) return;

	D2RL::Widgets::WidgetHandle mpPanel = D2RL::Widgets::InvalidHandle;
	if (gWidgets->findPanel(ctx, "D2RLoaderMultiplayerPanel", &mpPanel) != D2RL::Widgets::Result::Success || mpPanel == D2RL::Widgets::InvalidHandle) {
		return;
	}

	if (D2RL::HasWidgetServiceField(gWidgets, D2RL::WidgetServiceGetWidgetStateFieldEnd)) {
		D2RL::Widgets::State st {};
		if (gWidgets->getWidgetState(ctx, mpPanel, &st) == D2RL::Widgets::Result::Success && !st.visible) {
			return;
		}
	}

	D2RL::LogInfoF(ctx, "[castalia-autohost] D2RLoaderMultiplayerPanel visible! Applying mode='%s'...", gIntent.mode.c_str());

	if (gIntent.mode == "host") {
		TrySetInput(ctx, mpPanel, "GameName",
			{ "GameName", "GameNameInput", "GameNameTextBox", "HostGameName", "CreateGameName", "HostPanel/GameName", "HostGamePanel/GameName" },
			gIntent.gameName);
		TrySetInput(ctx, mpPanel, "Description",
			{ "GameDescription", "Description", "DescriptionInput", "HostGameDescription", "HostPanel/GameDescription" },
			gIntent.description);
		TrySetInput(ctx, mpPanel, "Password",
			{ "GamePassword", "Password", "PasswordInput", "HostGamePassword", "HostPanel/GamePassword" },
			gIntent.password);
		TrySetInput(ctx, mpPanel, "MaxPlayers",
			{ "MaxPlayers", "MaxPlayersInput", "PlayerCount", "MaxPlayerCount", "HostPanel/MaxPlayers" },
			std::to_string(gIntent.maxPlayers));
		TrySetDropdown(ctx, mpPanel, "Difficulty",
			{ "Difficulty", "DifficultyDropdown", "HostDifficulty", "GameDifficulty", "HostPanel/Difficulty" },
			static_cast<uint32_t>(gIntent.difficulty < 0 ? 0 : gIntent.difficulty));
		TrySetToggle(ctx, mpPanel, "Unlisted",
			{ "Unlisted", "UnlistedToggle", "UnlistedCheckbox", "UnlistedGame", "HostPanel/Unlisted" },
			gIntent.unlisted);
		TrySetToggle(ctx, mpPanel, "LanOnly",
			{ "LanOnly", "LanOnlyToggle", "LanOnlyCheckbox", "LocalOnly", "HostPanel/LanOnly" },
			gIntent.lanOnly);
		TrySetToggle(ctx, mpPanel, "LevelDiff",
			{ "LevelDifference", "LevelDiffToggle", "MaxLevelDiff", "CharacterLevelDiff", "HostPanel/LevelDifference" },
			gIntent.levelDiffEnabled);
	} else if (gIntent.mode == "join") {
		TrySetInput(ctx, mpPanel, "GameId",
			{ "GameId", "GameIdInput", "DirectJoinInput", "JoinGameId", "JoinAddress", "DirectJoinPanel/GameId" },
			gIntent.gameId);
	}

	gApplied.store(true);
}

static void ProbeWidgetsOnUiThread(const D2RL::PluginContext* ctx, void*) noexcept {
	if (ctx == nullptr || gWidgets == nullptr) return;
	D2RL::Widgets::WidgetHandle mpPanel = D2RL::Widgets::InvalidHandle;
	const auto pr = gWidgets->findPanel(ctx, "D2RLoaderMultiplayerPanel", &mpPanel);
	D2RL::LogInfoF(ctx, "[castalia-probe] findPanel(D2RLoaderMultiplayerPanel) -> %u (handle=%llu)",
		static_cast<unsigned>(pr), static_cast<unsigned long long>(mpPanel));
	if (pr != D2RL::Widgets::Result::Success) return;

	const char* probeNames[] = {
		"GameName", "GameNameInput", "GameDescription", "Description", "GamePassword", "Password",
		"Difficulty", "DifficultyDropdown", "MaxPlayers", "PlayerCount", "Unlisted", "UnlistedGame",
		"LanOnly", "LevelDifference", "GameId", "DirectJoin", "HostGame", "HostButton", "JoinButton",
		"BrowseGames", "HostPanel", "JoinPanel", "DirectJoinPanel", "CreateGameButton", "Tabs",
	};
	for (const char* n : probeNames) {
		D2RL::Widgets::WidgetHandle h = D2RL::Widgets::InvalidHandle;
		if (gWidgets->findWidget(ctx, mpPanel, n, &h) == D2RL::Widgets::Result::Success && h != D2RL::Widgets::InvalidHandle) {
			D2RL::LogInfoF(ctx, "[castalia-probe]   FOUND widget: %s (handle=%llu)", n, static_cast<unsigned long long>(h));
		}
	}
}

static auto CmdAutoHost(D2R::Game::Client*, const D2RL::ConsoleCommandContext* cmd, void*) noexcept -> D2RL::ConsoleCommandResult {
	if (cmd == nullptr || cmd->plugin == nullptr || gThreads == nullptr) return D2RL::ConsoleCommandResult::Failed;
	gIntent = LoadLaunchIntent();
	gApplied.store(false);
	gThreads->runOnUiThread(cmd->plugin, ApplyIntentOnUiThread, nullptr);
	cmd->plugin->WriteConsoleMessage("[castalia-autohost] Queued launch intent apply on UI thread.");
	return D2RL::ConsoleCommandResult::Handled;
}

static auto CmdProbe(D2R::Game::Client*, const D2RL::ConsoleCommandContext* cmd, void*) noexcept -> D2RL::ConsoleCommandResult {
	if (cmd == nullptr || cmd->plugin == nullptr || gThreads == nullptr) return D2RL::ConsoleCommandResult::Failed;
	gThreads->runOnUiThread(cmd->plugin, ProbeWidgetsOnUiThread, nullptr);
	cmd->plugin->WriteConsoleMessage("[castalia-probe] Probed D2RLoaderMultiplayerPanel (see d2rloader.log).");
	return D2RL::ConsoleCommandResult::Handled;
}

static void WatcherLoop() {
	while (gRunning.load() && !gApplied.load()) {
		std::this_thread::sleep_for(std::chrono::milliseconds(400));
		if (gRunning.load() && !gApplied.load() && gCtx != nullptr && gThreads != nullptr && gIntent.loaded) {
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
	context->RegisterConsoleCommand("castalia_autohost", CmdAutoHost, "Re-read launch intent and populate D2RLoaderMultiplayerPanel.");
	context->RegisterConsoleCommand("castalia_probe", CmdProbe, "Probe widget names inside D2RLoaderMultiplayerPanel.");

	if (gIntent.loaded) {
		D2RL::LogInfoF(context, "[castalia-autohost] Loaded launch intent: mode=%s game='%s' diff=%d max=%d",
			gIntent.mode.c_str(), gIntent.gameName.c_str(), gIntent.difficulty, gIntent.maxPlayers);
		gApplied.store(false);
		gRunning.store(true);
		gWatcher = std::thread(WatcherLoop);
	} else {
		context->LogInfo("[castalia-autohost] Loaded (no castalia_launch_intent.json present).");
	}
	return true;
}

D2RL_PLUGIN_EXPORT void D2RLoaderUnloadPlugin() noexcept {
	gRunning.store(false);
	if (gWatcher.joinable()) {
		gWatcher.join();
	}
	gCtx     = nullptr;
	gWidgets = nullptr;
	gThreads = nullptr;
}
