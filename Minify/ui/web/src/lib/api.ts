declare global {
  interface Window {
    pywebview: {
      api: PywebviewAPI
    }
  }
}

interface PywebviewAPI {
  patch(): Promise<ApiResult<null>>
  uninstall(): Promise<ApiResult<null>>
  get_mods(): Promise<ApiResult<Mod[]>>
  set_mod_enabled(mod: string, enabled: boolean, resolve_conflicts?: boolean): Promise<ApiResult<SetModEnabledResult>>
  get_mod_preview(mod: string): Promise<ApiResult<string | null>>
  get_mod_file_preview(mod: string, fileBase: string): Promise<ApiResult<string | null>>
  get_mod_notes_html(mod: string): Promise<ApiResult<string | null>>
  refresh_mods(): Promise<ApiResult<null>>
  get_settings(): Promise<ApiResult<SettingsPayload>>
  save_settings(data: SaveSettingsData): Promise<ApiResult<null>>
  get_mod_settings(mod: string): Promise<ApiResult<{ schema: SettingSchema[]; values: Record<string, unknown>; presets: ModPreset[]; preview_file?: string | null }>>
  save_mod_settings(mod: string, data: Record<string, unknown>): Promise<ApiResult<null>>
  run_mod_utility(mod: string, fn: string): Promise<ApiResult<{ text: string; type: string | null }[]>>
  reset_mod_settings(mod: string): Promise<ApiResult<Record<string, unknown>>>
  reset_all_mod_settings(): Promise<ApiResult<null>>
  get_localization(lang: string): Promise<ApiResult<Record<string, string>>>
  set_language(lang: string): Promise<ApiResult<null>>
  get_available_langs(): Promise<ApiResult<string[]>>
  resolve_steam_path(): Promise<ApiResult<{ path_known: boolean }>>
  get_steam_path_state(): Promise<ApiResult<{ path_known: boolean; resolving: boolean }>>
  get_steam_accounts(): Promise<ApiResult<SteamAccount[]>>
  get_app_info(): Promise<ApiResult<AppInfo>>
  open_url(url: string): Promise<ApiResult<null>>
  get_setup_state(): Promise<ApiResult<{ complete: boolean }>>
  save_setup(data: SetupData): Promise<ApiResult<null>>
  get_welcome_state(): Promise<ApiResult<{ show: boolean }>>
  dismiss_welcome(): Promise<ApiResult<null>>
  frontend_ready(): Promise<unknown>
  modal_respond(id: string, label: string): Promise<void>
  get_d2pfx_counts(): Promise<ApiResult<{total: number; enabled: number}>>
  get_d2pfx_categories(): Promise<ApiResult<D2pfxCategory[]>>
  get_d2pfx_mods(catId: string): Promise<ApiResult<D2pfxMod[]>>
  get_d2pfx_preview(catId: string, filename: string): Promise<ApiResult<string | null>>

  get_d2pfx_state(): Promise<ApiResult<{loading: boolean; loaded: boolean; error: string | null}>>
  reload_d2pfx(): Promise<ApiResult<boolean>>
  refresh_d2pfx_catalogue(): Promise<ApiResult<boolean>>
  clear_d2pfx_cache(): Promise<ApiResult<boolean>>
  get_d2pfx_selected_variants(): Promise<ApiResult<Record<string, string>>>
  set_d2pfx_selected_variants(data: Record<string, string>): Promise<ApiResult<Record<string, string>>>
  toggle_d2pfx_mod(modDirName: string, enabled: boolean, fileUrl?: string, isZip?: boolean, disableOthers?: string[]): Promise<ApiResult<null>>
  open_path(path: string, args?: string): Promise<ApiResult<null>>
  create_debug_zip(): Promise<ApiResult<null>>
  compile_assets(): Promise<ApiResult<null>>
  set_all_mods(enabled: boolean): Promise<ApiResult<null>>
  wipe_language_paths(): Promise<ApiResult<null>>
  extract_workshop_tools(): Promise<ApiResult<null>>
  launch_steam(): Promise<ApiResult<null>>
  kill_steam(): Promise<ApiResult<null>>
  validate_dota2(): Promise<ApiResult<null>>
  select_compile_dir(): Promise<ApiResult<string | null>>
  compile_from_custom(): Promise<ApiResult<null>>
  reset_settings(): Promise<ApiResult<null>>
  open_file_dialog(fileTypes?: string): Promise<ApiResult<string | null>>
  restart_steam_and_apply(data: ApplyLaunchOptionsData): Promise<ApiResult<RestartSteamResult>>
  get_setup_data(): Promise<ApiResult<SetupData>>
  setup_flow_done(waiterId: string, result: string): Promise<void>
  set_ui_zoom(zoom: number): Promise<ApiResult<null>>
}

// ── Discriminated union result type ──────────────────────────────────────────

export type ApiOk<T> = { ok: true; data: T; error: null }
export type ApiErr   = { ok: false; data: null; error: string }
export type ApiResult<T> = ApiOk<T> | ApiErr

// ── Domain types ──────────────────────────────────────────────────────────────

export type ModStatus = 'working' | 'broken' | 'minor_issues'

export interface Mod {
  name: string
  raw_name: string
  enabled: boolean
  always: boolean
  unsupported: boolean
  hasNotes: boolean
  hasPreview: boolean
  version: string
  tags: string[]
  status: ModStatus
  hasSettings: boolean
  socialLinks: Record<string, string>
  author: string
}

export interface CardItem {
  id: string
  name: string
  displayName?: string
  author?: string
  tags: string[]
  version?: string
  status?: ModStatus
  isBase?: boolean
  unsupported?: boolean
  enabled: boolean
  hasSettings?: boolean
  hasPreview?: boolean
  hasNotes?: boolean
}

export interface SetModEnabledResult {
  needs_confirmation?: boolean
  conflicts?: string[]
  disabled?: string[]
}

export interface SteamAccount {
  id: string
  name: string
}

export interface SetupData {
  lang?: string
  game_lang?: string
  steam_ids?: string[]
}

export interface ApplyLaunchOptionsData {
  steam_ids: string[]
  locale: string
}

export type LaunchOptionStatus = 'ok' | 'already_set' | 'no_vdf' | 'no_dota_data' | 'no_steam_root' | 'permission_error' | 'error'

export interface LaunchOptionResult {
  steam_id: string
  name: string
  status: LaunchOptionStatus
  launch_options?: string
}

export interface RestartSteamResult {
  apply_results: LaunchOptionResult[]
  restart_needed: boolean
  steam_killed: boolean
  steam_exited: boolean
  steam_launched: boolean
}

export interface AppInfo {
  version: string
  title: string
  discord: string
  telegram: string
  github_io: string
  output_list: string[]
  output_names: Record<string, string>
  locale_aliases: Record<string, string>
  current_output: string
  current_lang: string
}

export interface SettingSchema {
  key: string
  text: string
  default: unknown
  type: string
  advanced?: boolean
  section?: string
  description?: string
  depends_on?: string
  when?: { key: string; value?: unknown }
  file_types?: string
  items?: unknown[]
  min?: number
  max?: number
  step?: number
  constrain?: boolean
}

export interface ModPreset {
  name: string
  description?: string
  values: Record<string, unknown>
}

export interface SettingsPayload {
  schema: {
    global: SettingSchema[]
    mods: Record<string, never>
  }
  values: {
    global: Record<string, unknown>
    mods: Record<string, never>
  }
  showAdvanced: boolean
}

export interface SaveSettingsData {
  global: Record<string, unknown>
  showAdvanced?: boolean
}

// ── D2PFX Browser types ──────────────────────────────────────────────────────

export interface D2pfxCategory {
  id: string
  name: string
  description: string
}

export interface D2pfxVariant {
  label: string
  color?: string
  preview?: string
  fileUrl?: string
  isZip: boolean
  modDirName: string
  enabled: boolean
}

export interface D2pfxMod {
  name: string
  label?: string
  author?: string | string[]
  sender?: string | string[]
  tags: string[]
  preview?: string
  fileUrl?: string
  isZip: boolean
  modDirName: string
  enabled: boolean
  variants?: D2pfxVariant[]
}
