#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_gui_extra/juce_gui_extra.h>
#include "MainComponent.h"
#include <iostream>

class OpenDAWApplication : public juce::JUCEApplication
{
public:
    OpenDAWApplication() = default;

    const juce::String getApplicationName() override
    {
        return "OpenDAW";
    }

    const juce::String getApplicationVersion() override
    {
        return "0.1.0";
    }

    bool moreThanOneInstanceAllowed() override
    {
        return false;
    }

    void initialise(const juce::String& commandLine) override
    {
        std::cout << "OpenDAWApplication::initialise - START" << std::endl;
        DBG("OpenDAWApplication::initialise - creating MainWindow");
        mainWindow.reset(new MainWindow(getApplicationName()));
        DBG("OpenDAWApplication::initialise - MainWindow created");
        std::cout << "OpenDAWApplication::initialise - END" << std::endl;
    }

    void shutdown() override
    {
        mainWindow = nullptr;
    }

    void systemRequestedQuit() override
    {
        quit();
    }

    void anotherInstanceStarted(const juce::String& commandLine) override
    {
    }

    class MainWindow : public juce::DocumentWindow
    {
    public:
        explicit MainWindow(const juce::String& name)
            : DocumentWindow(name,
                             juce::Desktop::getInstance().getDefaultLookAndFeel()
                                 .findColour(ResizableWindow::backgroundColourId),
                             DocumentWindow::allButtons)
        {
            std::cout << "MainWindow constructor - START" << std::endl;
            DBG("MainWindow constructor - starting");
            setUsingNativeTitleBar(true);
            DBG("MainWindow constructor - creating MainComponent");
            setContentOwned(new MainComponent(), true);
            DBG("MainWindow constructor - MainComponent created");
            setResizable(true, true);
            centreWithSize(1200, 800);
            setVisible(true);
            DBG("MainWindow constructor - complete");
            std::cout << "MainWindow constructor - END" << std::endl;
        }

        void closeButtonPressed() override
        {
            JUCEApplication::getInstance()->systemRequestedQuit();
        }

    private:
        JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MainWindow)
    };

private:
    std::unique_ptr<MainWindow> mainWindow;
};

START_JUCE_APPLICATION(OpenDAWApplication)
