import os
import sys
import enum
import signal
import pickle
import collections
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import seabreeze.spectrometers
from matplotlib.animation import FuncAnimation

mpl.rcParams['keymap.pan'].remove('p')
mpl.rcParams['keymap.save'].remove('s')
mpl.rcParams['keymap.home'].remove('h')
mpl.rcParams['keymap.fullscreen'].remove('f')


class SpectrometerLiveView: 

    class Mode(enum.Enum):
        INTENSITY = 0
        TRANSMITTANCE = 1
        ABSORBANCE = 2

    YRANGE_PARAM = {
            Mode.INTENSITY : 
            { 
                'default' : 4000,
                'step'    : 500,
                'min'     : 500,
                },
            Mode.TRANSMITTANCE: 
            {
                'default' : 1.1, 
                'step'    : 0.1, 
                'min'     : 0.1,
                },
            Mode.ABSORBANCE :
            {
                'default' : 1.1, 
                'step'    : 0.1, 
                'min'     : 0.1,
                }
            }

    INTEG_TIME_PARAM = { 
            'default' : 4000,
            'step'    : 1000,
            'min'     : 3000,
            }

    LINE_COLOR = {
            'liveview' : 'b', 
            'blanking' : 'g', 
            'peak'     : 'r',
            }

    MODE_TO_YLABEL = {
            Mode.INTENSITY     : 'Intensity', 
            Mode.TRANSMITTANCE : 'Transmittance', 
            Mode.ABSORBANCE    : 'Absorbance',
            }
    
    MODE_TO_YRANGE_DEFAULT = {
            Mode.INTENSITY     :  YRANGE_PARAM[Mode.INTENSITY]['default'], 
            Mode.TRANSMITTANCE :  YRANGE_PARAM[Mode.TRANSMITTANCE]['default'], 
            Mode.ABSORBANCE    :  YRANGE_PARAM[Mode.ABSORBANCE]['default'], 
            }

    INTENSITY_THRESHOLD = 1

    SAVE_DIRECTORY = 'data'
    DATA_FILENAME = 'data.pkl'
            
    def __init__(self):

        self.spectrometer = seabreeze.spectrometers.Spectrometer.from_first_available()
        self.integ_window = self.INTEG_TIME_PARAM['default']
        self.spectrometer.integration_time_micros(self.integ_window)
        self.wavelengths = self.spectrometer.wavelengths()
        self.blanking_intensities = None
        self.current_mode = self.Mode.INTENSITY
        self.peakfinder_enabled = False
        self.data = {}

        self.fig, self.ax = plt.subplots(1,1)
        self.liveview_line, = self.ax.plot([],[], self.LINE_COLOR['liveview'])
        self.blanking_line, = self.ax.plot([],[], self.LINE_COLOR['blanking'])
        self.peakfind_line, = self.ax.plot([],[], self.LINE_COLOR['peak'])
        
        self.ax.set_xlim(self.wavelengths.min(), self.wavelengths.max()) 
        self.ax.set_ylim(0, self.YRANGE_PARAM[self.current_mode]['default']) 
        self.ax.set_xlabel('Wavelength (nm)')
        self.ax.set_ylabel(self.MODE_TO_YLABEL[self.current_mode])
        self.ax.grid(True)

        self.sigint = False
        signal.signal(signal.SIGINT, self.sigint_handler)

        self.event_key_to_callback = collections.OrderedDict([
                ('s'    , self.save), 
                ('f'    , self.save_figure),
                ('b'    , self.blank),
                ('c'    , self.clear_blank),
                ('up'   , self.increase_y_range),
                ('down' , self.decrease_y_range) ,
                ('i'    , self.set_mode_to_intensity) ,
                ('t'    , self.set_mode_to_transmittance), 
                ('a'    , self.set_mode_to_absorbance),
                ('p'    , self.toggle_peakfinder),
                ('.'    , self.increase_integ_window),
                (','    , self.decrease_integ_window) ,
                ('h'    , self.print_help),
                ])

        self.event_key_to_doc = collections.OrderedDict([
                ('s'    ,   'save data'),
                ('f'    ,   'save current figure'),
                ('b'    ,   'acquire blanking data'),
                ('c'    ,   'clear blanking data'),
                ('up'   ,   'increase plot y axis range'),
                ('down' ,   'decrease plot y axis range'),
                ('i'    ,   'display intensity vs wavelength'),
                ('t'    ,   'display transmittance vs wavelength'),
                ('a'    ,   'display absorbance vs wavelength'),
                ('p'    ,   'toggle on/off peak finder'),
                ('<'    ,   'increase integration window') ,
                ('>'    ,   'decrease integration window') ,
                ('h'    ,   'print help message') ,
                ('q'    ,   'quit'),
                ])

        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)

        self.print_help()


    def on_key_press(self, event):
        """
        Switchyard for handling key press events
        """
        #print(event.key)
        try:
            self.event_key_to_callback[event.key]()
        except KeyError:
            pass
            #print(f'KeyError: {event.key}')

    def save(self):
        """
        Save data.
        """
        os.makedirs(self.SAVE_DIRECTORY, exist_ok=True)
        data_file = os.path.join(os.curdir, self.SAVE_DIRECTORY, self.DATA_FILENAME)
        with open(data_file, 'wb') as f:
            pickle.dump(self.data, f)
        print(f'data saved to: {data_file}')

    def save_figure(self):
        """
        Save figure
        """
        os.makedirs(self.SAVE_DIRECTORY, exist_ok=True)
        mode_str = self.MODE_TO_YLABEL[self.current_mode].lower()
        if self.peakfinder_enabled: 
            fig_filename = f'{mode_str}_w_peak.png'
        else:
            fig_filename = f'{mode_str}.png'
        fig_filename = os.path.join(os.curdir, self.SAVE_DIRECTORY, fig_filename)
        self.fig.savefig(fig_filename)
        print(f'figure saved to: {fig_filename}')

    def blank(self):
        """
        Save blanking intensities for use during absorbance mode.
        """
        if self.current_mode == self.Mode.INTENSITY:
            _, self.blanking_intensities  = self.liveview_line.get_data()
            print('blanking data acquired')
        else:
            print("can't acquire blanking data - must be in intensity mode")

    def clear_blank(self):
        """
        Clear blanking intentities
        """
        if self.current_mode == self.Mode.INTENSITY:
            self.blanking_intensities = None
            print('blanking data cleared')
        else:
            print("can't clear blanking data - must be in intensity mode")


    def increase_y_range(self):
        """
        Increase the live view plot's y range by one step size.
        """
        y_min, y_max = self.ax.get_ylim()
        y_max_new = y_max + self.YRANGE_PARAM[self.current_mode]['step']
        self.ax.set_ylim(y_min, y_max_new)
        print(f'y range = {y_max_new}')

    def decrease_y_range(self):
        """
        Decrease the live view plot's y range by one step size until
        the minimum size is reached. 
        """
        y_min, y_max = self.ax.get_ylim()
        step = self.YRANGE_PARAM[self.current_mode]['step']
        minval = self.YRANGE_PARAM[self.current_mode]['min']
        y_max_new = max(y_max - step, minval)
        self.ax.set_ylim(y_min, y_max_new)
        print(f'y range = {y_max_new}')

    def set_mode_to_intensity(self):
        """
        Set display mode to intensity
        """
        self.current_mode = self.Mode.INTENSITY
        self.reset_y_axis()

    def set_mode_to_transmittance(self):
        """
        Set display mode to transmittance
        """
        if self.blanking_intensities is None:
            print('unable to display absorbance - no blanking data')
        else:
            self.current_mode = self.Mode.TRANSMITTANCE
            self.reset_y_axis()

    def set_mode_to_absorbance(self):
        """
        Set mode to display absorbance
        """
        if self.blanking_intensities is None:
            print('unable to display absorbance - no blanking data')
        else:
            self.current_mode = self.Mode.ABSORBANCE
            self.reset_y_axis()

    def reset_y_axis(self):
        self.ax.set_ylim(0, self.YRANGE_PARAM[self.current_mode]['default']) 
        self.ax.set_ylabel(self.MODE_TO_YLABEL[self.current_mode])

    def toggle_peakfinder(self):
        if self.peakfinder_enabled:
            try:
                print(f"max intensity:     {self.data['maximum_intensity']}")
            except KeyError:
                pass
            try:
                print(f"min transmittance: {self.data['minimum_transmittance']}")
            except KeyError:
                pass
            try:
                print(f"max absorbance:    {self.data['maximum_absorbance']}")
            except KeyError:
                pass
        self.peakfinder_enabled = not self.peakfinder_enabled
        print(f'peak finder enabled = {self.peakfinder_enabled}')

    def print_help(self):
        """
        Prints a help message displaying the hot keys and describing
        their associated commands.
        """
        print()
        print('commands')
        print('------------------------------------------')
        for k, v in self.event_key_to_doc.items():
            print(f'{k} \t =  {v}')
        print('------------------------------------------')
        print()

    def increase_integ_window(self):
        """
        Increase the spectrometer integration window by one step
        """
        self.integ_window += self.INTEG_TIME_PARAM['step']
        self.spectrometer.integration_time_micros(self.integ_window)
        print(f'integration window = {self.integ_window}')
        

    def decrease_integ_window(self):
        """
        Decrease the spectrometer integration window by one step
        """
        self.integ_window -= self.INTEG_TIME_PARAM['step']
        self.integ_window = max(self.integ_window, self.INTEG_TIME_PARAM['min'])
        self.spectrometer.integration_time_micros(self.integ_window)
        print(f'integration window = {self.integ_window}')

    def update(self, frame):
        """
        Read intensities from sensor and update live plot
        """
        if self.sigint:
            print('quiting ... googbye')
            exit(0)

        self.data = {}
        line_update_list = []

        # Read data from spectrometer and save in data dict
        intensities = self.spectrometer.intensities()
        maximum_intensity = self.find_peak(self.wavelengths, intensities)
        self.data['mode'] = self.MODE_TO_YLABEL[self.current_mode].lower()
        self.data['wavelengths'] = self.wavelengths 
        self.data['intensities'] = intensities 
        self.data['maximum_intensity'] =  maximum_intensity
        if self.blanking_intensities is not None:
            mask = self.blanking_intensities > self.INTENSITY_THRESHOLD
            transmittance = intensities[mask]/self.blanking_intensities[mask]
            absorbance = -np.log10(transmittance)
            wavelengths_masked = self.wavelengths[mask]
            minimum_transmittance = self.find_peak(wavelengths_masked, transmittance, 'min')
            maximum_absorbance = self.find_peak(wavelengths_masked, absorbance, 'max')
            self.data['mask'] = mask
            self.data['tramsmittance'] = transmittance
            self.data['absorbance'] = absorbance
            self.data['wavelengths_masked'] = wavelengths_masked
            self.data['minimum_transmittance'] = minimum_transmittance
            self.data['maximum_absorbance'] = maximum_absorbance
            self.data['blanking_intensities'] = self.blanking_intensities

        # Get liveview, blanking and peakfind x,y data based on mode
        liveview_x, liveview_y = [], []
        blanking_x, blanking_y = [], []
        peakfind_x, peakfind_y = [], []
        if self.current_mode == self.Mode.INTENSITY:
            liveview_x = self.wavelengths
            liveview_y = intensities
            peak_x_val, peak_y_val = maximum_intensity
            if self.blanking_intensities is not None:
                blanking_x = self.wavelengths
                blanking_y = self.blanking_intensities
        elif self.current_mode == self.Mode.TRANSMITTANCE: 
            liveview_x = self.wavelengths[mask] 
            liveview_y = transmittance 
            peak_x_val, peak_y_val = minimum_transmittance
        elif self.current_mode == self.Mode.ABSORBANCE: 
            liveview_x = self.wavelengths[mask] 
            liveview_y = absorbance 
            peak_x_val, peak_y_val = maximum_absorbance
        if self.peakfinder_enabled: 
            peakfind_x = [peak_x_val, peak_x_val]
            peakfind_y = [0.0, 1.1*peak_y_val.max()]

        # Update live view and blanking lines
        self.liveview_line.set_data(liveview_x, liveview_y)
        line_update_list.append(self.liveview_line)
        self.blanking_line.set_data(blanking_x, blanking_y)
        line_update_list.append(self.blanking_line)
        self.peakfind_line.set_data(peakfind_x, peakfind_y)
        line_update_list.append(self.peakfind_line)
        return line_update_list 

    def find_peak(self, x, y, peak_type='max'):
        if peak_type == 'max':
            ind = y.argmax()
        else:
            ind = y.argmin()
        peak_x = x[ind]
        peak_y = y[ind]
        return peak_x, peak_y

    def sigint_handler(self, signum, frame):
        """
        Handle SIGINT in order to quit properly
        """
        self.sigint = True

    def run(self):
        """
        Start the live view
        """
        animation = FuncAnimation(self.fig, self.update, interval=1)
        plt.show()


def main():
    live_view = SpectrometerLiveView()
    live_view.run()


# ----------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
