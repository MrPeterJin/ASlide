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
    
    # For qptiff files which have specific biomarker channels
    print('biomarkers: ', slide.get_biomarkers())
    biomarkers = slide.get_biomarkers()
    region = slide.read_region((0, 0), 0, (512, 512)) # if not specified, read_region defaultly reads the first biomarker channel (usually 'DAPI')
    region.save('test_output.png')
    
    print('reading region with specific biomarker...')
    region_biomarker = slide.read_region_biomarker((0, 0), 0, (512, 512), biomarkers[1])
    region_biomarker.save('test_output_{}.png'.format(biomarkers[1]))

print('done')
