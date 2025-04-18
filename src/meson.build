pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'whisper'
gnome = import('gnome')

# Compile Blueprint files
blueprints = custom_target('blueprints',
  input: files(
    'gtk/help-overlay.blp',
    'window.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

gnome.compile_resources('whisper',
  'whisper.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: blueprints,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'whisper.in',
  output: 'whisper',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

whisper_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'database_manager.py',
]

install_data(whisper_sources, install_dir: moduledir)

# Install migrations
migrations_dir = moduledir / 'migrations'
install_data('migrations/20250414223100_create_recordings_table.sql', install_dir: migrations_dir)
