+ PLATFORM:@MODULE_OS_NAME@ MAYAVERSION:@MAYA_VERSION@ @PROJECT_NAME@ @PROJECT_VERSION@ ./@MODULE_FULL_NAME@
MMSOLVER_LOCATION :=
MMSOLVER_CREATE_SHELF = 1
MMSOLVER_HELP_SOURCE = internet
MMSOLVER_DEFAULT_SOLVER = @DEFAULT_SOLVER@
MAYA_CUSTOM_TEMPLATE_PATH +:= scripts/AETemplates
LD_LIBRARY_PATH +:= lib
PYTHONPATH +:= python
[r] scripts: scripts
