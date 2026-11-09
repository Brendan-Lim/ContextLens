// Disposable diagnostic only. Private CoreGraphics interfaces, as documented by
// Chromium's BSD-licensed virtual_display_util_mac.mm. No production linkage.
#import <AppKit/AppKit.h>
#import <CoreGraphics/CoreGraphics.h>
@interface CGVirtualDisplayDescriptor : NSObject
@property unsigned int vendorID, productID, serialNum, serialNumber;
@property(strong) NSString *name;
@property CGSize sizeInMillimeters;
@property unsigned int maxPixelsWide, maxPixelsHigh;
@property CGPoint redPrimary, greenPrimary, bluePrimary, whitePoint;
@property(strong) id queue;
@end
@interface CGVirtualDisplaySettings : NSObject
@property(strong) NSArray *modes;
@property unsigned int hiDPI;
@end
@interface CGVirtualDisplayMode : NSObject
- (id)initWithWidth:(unsigned int)width height:(unsigned int)height refreshRate:(double)rate;
@end
@interface CGVirtualDisplay : NSObject
@property(readonly) unsigned int displayID;
- (id)initWithDescriptor:(CGVirtualDisplayDescriptor *)descriptor;
- (BOOL)applySettings:(CGVirtualDisplaySettings *)settings;
@end
static void save(NSDictionary *value, NSString *path) {
    NSData *data=[NSJSONSerialization dataWithJSONObject:value options:NSJSONWritingPrettyPrinted error:nil];
    [data writeToFile:path atomically:YES];
}
int main(int argc,const char **argv) { @autoreleasepool {
    if (![NSProcessInfo.processInfo.environment[@"GITHUB_ACTIONS"] isEqual:@"true"] || argc!=2) return 2;
    NSString *path=@(argv[1]);
    if (!NSClassFromString(@"CGVirtualDisplay")) { save(@{@"status":@"private API unavailable"},path); return 3; }
    CGVirtualDisplayDescriptor *d=[CGVirtualDisplayDescriptor new];
    d.name=@"ContextLens disposable Retina"; d.vendorID=505; d.productID=9;
    d.serialNum=20261109; d.serialNumber=20261109;
    d.maxPixelsWide=3840; d.maxPixelsHigh=2160;
    d.sizeInMillimeters=CGSizeMake(443,249);
    d.redPrimary=CGPointMake(.64,.33); d.greenPrimary=CGPointMake(.30,.60);
    d.bluePrimary=CGPointMake(.15,.06); d.whitePoint=CGPointMake(.3127,.3290);
    d.queue=dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0);
    CGVirtualDisplay *display=[[CGVirtualDisplay alloc] initWithDescriptor:d];
    if (!display) { save(@{@"status":@"virtual display creation refused"},path); return 4; }
    CGVirtualDisplaySettings *settings=[CGVirtualDisplaySettings new]; settings.hiDPI=1;
    settings.modes=@[[[CGVirtualDisplayMode alloc] initWithWidth:1920 height:1080 refreshRate:60]];
    BOOL applied=[display applySettings:settings];
    [NSThread sleepForTimeInterval:3];
    CGDirectDisplayID old=CGMainDisplayID();
    CGDisplayConfigRef config=NULL; CGError status=CGBeginDisplayConfiguration(&config);
    if (status==kCGErrorSuccess) {
        CGConfigureDisplayOrigin(config,display.displayID,0,0);
        if (old!=display.displayID) CGConfigureDisplayOrigin(config,old,1920,0);
        status=CGCompleteDisplayConfiguration(config,kCGConfigureForSession);
    }
    save(@{@"status":@"created",@"applied":@(applied),@"displayID":@(display.displayID),@"configurationStatus":@(status),@"requestedPointWidth":@1920,@"requestedPointHeight":@1080,@"requestedPixelWidth":@3840,@"requestedPixelHeight":@2160},path);
    // Retain the virtual display until this process exits; session-only changes.
    [[NSRunLoop currentRunLoop] run];
    (void)display;
    return 0;
} }
