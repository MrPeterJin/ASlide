from Aslide.aslide import Slide

print('running test...')

slides = ['path-to-your-slides1', 'path-to-your-slides2']

for slide in slides:
    print('filepath: ', slide)
    slide = Slide(slide)
    print('level_count: ', slide.level_count)
    print('level_dimensions: ', slide.level_dimensions)
    print('level_downsamples: ', slide.level_downsamples)
    print('best_downsample_at_64:', slide.get_best_level_for_downsample(64))
    print('='*50)

print('done')
