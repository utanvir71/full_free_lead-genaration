document.addEventListener("DOMContentLoaded", () => {
  const state = document.querySelector("#state");
  const city = document.querySelector("#city");

  if (!(state instanceof HTMLSelectElement) || !(city instanceof HTMLSelectElement)) {
    return;
  }

  const setPlaceholder = (label) => {
    city.replaceChildren(new Option(label, ""));
  };

  const loadCities = async (stateCode, selectedCity = "") => {
    city.disabled = true;
    setPlaceholder("Loading cities…");
    try {
      const response = await fetch(
        `/runs/cities/${encodeURIComponent(stateCode)}`,
        { headers: { Accept: "application/json" } },
      );
      if (!response.ok) {
        setPlaceholder("Unable to load cities");
        return;
      }
      const payload = await response.json();
      setPlaceholder("Select a city");
      for (const cityName of payload.cities) {
        city.add(new Option(cityName, cityName, false, cityName === selectedCity));
      }
      city.disabled = false;
    } catch {
      setPlaceholder("Unable to load cities");
    }
  };

  state.addEventListener("change", () => {
    if (!state.value) {
      city.disabled = true;
      setPlaceholder("Select a state first");
      return;
    }
    void loadCities(state.value);
  });

  if (state.value) {
    void loadCities(state.value, city.dataset.selectedCity ?? "");
  }
});
