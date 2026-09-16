project(
  'edrxdr-bluefield-agent',
  'c',
  version: '0.1.0',
  default_options: ['c_std=c11']
)

doca_common = dependency('doca-common')

executable(
  'bluefield_monitor',
  'src/bluefield_monitor.c',
  dependencies: [
    doca_common
  ]
)
