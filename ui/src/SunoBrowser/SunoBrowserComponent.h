#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_gui_extra/juce_gui_extra.h>

class SunoBrowserComponent : public juce::Component,
                             public juce::TableListBoxModel,
                             public juce::TextEditor::Listener,
                             public juce::Button::Listener
{
public:
    SunoBrowserComponent();
    ~SunoBrowserComponent() override;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // TableListBoxModel interface
    int getNumRows() override;
    void paintRowBackground(juce::Graphics& g, int rowNumber, int width, int height, bool rowIsSelected) override;
    void paintCell(juce::Graphics& g, int rowNumber, int columnId, int width, int height, bool rowIsSelected) override;
    juce::Component* refreshComponentForCell(int rowNumber, int columnId, bool isRowSelected, juce::Component* existingComponentToUpdate) override;

    // TextEditor::Listener
    void textEditorTextChanged(juce::TextEditor& editor) override;

    // Button::Listener
    void buttonClicked(juce::Button* button) override;

    // Load tracks from API
    void loadTracks();
    void searchTracks(const juce::String& query, const juce::String& genre, int tempoMin, int tempoMax);

    // Callback when track is imported (includes downloaded file path)
    std::function<void(const juce::String& trackId, int targetTrack, int targetScene, const juce::String& audioFilePath)> onTrackImported;

private:
    // UI Components
    juce::Label titleLabel;
    juce::TextEditor searchEditor;
    juce::ComboBox genreComboBox;
    juce::Slider tempoMinSlider;
    juce::Slider tempoMaxSlider;
    juce::Label tempoRangeLabel;
    juce::Label statusLabel;
    juce::TableListBox trackTable;
    juce::TextButton refreshButton;
    juce::TextButton importButton;

    // Track data
    struct TrackInfo
    {
        juce::String id;
        juce::String title;
        juce::String artist;
        juce::String genre;
        int tempo;
        juce::String key;
        juce::String audioPath;
    };

    std::vector<TrackInfo> tracks;
    int selectedRow = -1;

    // Column IDs
    enum ColumnIds
    {
        TitleColumn = 1,
        ArtistColumn,
        GenreColumn,
        TempoColumn,
        KeyColumn,
        ActionColumn
    };

    // HTTP API
    void fetchTracksFromAPI();
    void parseTracksResponse(const juce::String& jsonResponse);

    void importSelectedTrack();
    void loadMockData();
    static constexpr int headerHeight = 40;
    static constexpr int filterHeight = 30;
    static constexpr int buttonWidth = 80;
    static constexpr int rowHeight = 30;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(SunoBrowserComponent)
};
