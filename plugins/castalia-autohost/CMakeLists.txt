cmake_minimum_required(VERSION 3.25)
project(castalia-autohost VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
set(D2RLPLUGIN_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(D2RLPLUGIN_BUILD_TESTS OFF CACHE BOOL "" FORCE)

FetchContent_Declare(
  D2RLPluginSDK
  GIT_REPOSITORY https://github.com/D2RLoader/PluginSDK.git
  GIT_TAG        master
  GIT_SHALLOW    TRUE
)
FetchContent_MakeAvailable(D2RLPluginSDK)

add_library(castalia-autohost SHARED
  src/castalia_autohost.cpp
)

target_link_libraries(castalia-autohost PRIVATE D2RLPlugin::D2RLPlugin)

set_target_properties(castalia-autohost PROPERTIES
  OUTPUT_NAME "castalia-autohost"
)

if(MSVC)
  target_compile_options(castalia-autohost PRIVATE /W3 /permissive- /EHsc)
endif()
