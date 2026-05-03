#include "SettingsManager.h"

namespace OpenDAW {

juce::File SettingsManager::getSettingsFile()
{
    auto configDir = juce::File::getSpecialLocation(juce::File::userApplicationDataDirectory)
                        .getChildFile("OpenDAW");
    
    if (!configDir.exists())
        configDir.createDirectory();
    
    return configDir.getChildFile("settings.json");
}

juce::var SettingsManager::loadSettings()
{
    auto file = getSettingsFile();
    
    if (!file.existsAsFile())
        return juce::var(new juce::DynamicObject());
    
    auto json = file.loadFileAsString();
    auto result = juce::JSON::parse(json);
    
    if (result.wasOk())
        return result.getResult();
    
    return juce::var(new juce::DynamicObject());
}

void SettingsManager::saveSettings(const juce::var& settings)
{
    auto file = getSettingsFile();
    auto json = juce::JSON::toString(settings);
    file.replaceWithText(json);
}

juce::var SettingsManager::getSettingsObject()
{
    static juce::var settings = loadSettings();
    return settings;
}

bool SettingsManager::isFirstLaunch()
{
    return !getSettingsFile().existsAsFile();
}

void SettingsManager::markOnboardingComplete()
{
    auto settings = loadSettings();
    
    if (auto* obj = settings.getDynamicObject())
    {
        obj->setProperty("onboardingComplete", true);
        saveSettings(settings);
    }
}

bool SettingsManager::shouldShowOnboarding()
{
    if (isFirstLaunch())
        return true;
    
    auto settings = loadSettings();
    
    if (auto* obj = settings.getDynamicObject())
    {
        bool onboardingComplete = obj->getProperty("onboardingComplete");
        bool showOnStartup = obj->getProperty("showOnboardingOnStartup");
        
        return showOnStartup && !onboardingComplete;
    }
    
    return true;
}

void SettingsManager::setShowOnboardingOnStartup(bool show)
{
    auto settings = loadSettings();
    
    if (auto* obj = settings.getDynamicObject())
    {
        obj->setProperty("showOnboardingOnStartup", show);
        saveSettings(settings);
    }
}

juce::String SettingsManager::getLastProjectPath()
{
    auto settings = loadSettings();
    
    if (auto* obj = settings.getDynamicObject())
    {
        return obj->getProperty("lastProjectPath").toString();
    }
    
    return {};
}

void SettingsManager::setLastProjectPath(const juce::String& path)
{
    auto settings = loadSettings();
    
    if (auto* obj = settings.getDynamicObject())
    {
        obj->setProperty("lastProjectPath", path);
        saveSettings(settings);
    }
}

juce::var SettingsManager::getSetting(const juce::String& key, const juce::var& defaultValue)
{
    auto settings = loadSettings();
    
    if (auto* obj = settings.getDynamicObject())
    {
        auto value = obj->getProperty(key);
        if (!value.isUndefined())
            return value;
    }
    
    return defaultValue;
}

void SettingsManager::setSetting(const juce::String& key, const juce::var& value)
{
    auto settings = loadSettings();
    
    if (auto* obj = settings.getDynamicObject())
    {
        obj->setProperty(key, value);
        saveSettings(settings);
    }
}

} // namespace OpenDAW
